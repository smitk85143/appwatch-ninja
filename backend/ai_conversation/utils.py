import json
from datetime import timedelta
from django.conf import settings
from django.db.models import Q
from langchain_ollama import ChatOllama
from django.http import StreamingHttpResponse
from asgiref.sync import sync_to_async
from django.utils import timezone

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import tools_condition

from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableLambda
from langgraph.prebuilt import ToolNode

import uuid
from typing import Annotated

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig
from langgraph.graph.message import AnyMessage, add_messages
from typing_extensions import TypedDict

from home.models import AppDetail
from home.schemas import AppDetailSchema
from . import models


llm = ChatOllama(
    base_url=settings.OLLAMA_BASE_URL,
    model="llama3.2:1b",
    temperature=0,
)

def get_app_informations(query_app_name: str) -> dict:
    """Fetches an app informations by name and returns app details."""
    try:
        app = AppDetail.objects.filter(name__icontains=query_app_name).first()

        if not app:
            return {}
        app_data = {
            "name": app.name,
            "description": app.description,
            "userAvgRating": app.userAvgRating,
            "genre": app.genre.genre,
            "current version": app.currentVersion,
            "current version date": app.currentVersionDate,
            "released date": app.released,
            "rating distribution [1 star, 2 star, 3 star, 4 star, 5 star]": app.histogram,
        }
        return app_data

    except Exception:
        return {}


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


class Assistant:
    def __init__(self, runnable: Runnable):
        """
        Initialize the Assistant with a runnable object.

        Args:
            runnable (Runnable): The runnable instance to invoke.
        """
        self.runnable = runnable

    def __call__(self, state: State, config: RunnableConfig):
        """
        Call method to invoke the LLM and handle its responses.
        Re-prompt the assistant if the response is not a tool call or meaningful text.

        Args:
            state (State): The current state containing messages.
            config (RunnableConfig): The configuration for the runnable.

        Returns:
            dict: The final state containing the updated messages.
        """
        while True:
            result = self.runnable.invoke(state)  # Invoke the LLM
            if not result.tool_calls and (
                not result.content
                or isinstance(result.content, list)
                and not result.content[0].get("text")
            ):
                messages = state["messages"] + [("user", "Respond with a real output.")]
                state = {**state, "messages": messages}
            else:
                break
        return {"messages": result}


# Create the primary assistant prompt template
primary_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an intelligent assistant specializing in providing detailed and accurate information about mobile applications. "
            "You can answer user queries regarding app details, such as the app's name, description, rating, developer, genre, installs, and other relevant features. "
            "Please provide concise, informative, and professional responses. If a user asks about something unrelated to apps, kindly inform them that you can only assist with app-related queries. "
            "If you do not have enough information to answer a specific question, let the user know politely and guide them to ask for app-related details."
            "You have access to one tools: get_app_informations. "
            "For any user questions about app information, use the get_app_informations tool to get information about app. "
        ),
        ("placeholder", "{messages}"),
    ]
)

# Prompt our LLM and bind tools
assistant_runnable = primary_assistant_prompt | llm.bind_tools([get_app_informations])


def create_tool_node_with_fallback(tools: list) -> dict:
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )


def handle_tool_error(state: State) -> dict:
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\n please fix your mistakes.",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ]
    }

# Graph
builder = StateGraph(State)

# Define nodes: these do the work
builder.add_node("assistant", Assistant(assistant_runnable))
builder.add_node("tools", create_tool_node_with_fallback([get_app_informations]))

# Define edges: these determine how the control flow moves
builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant",
    # If the latest message (result) from assistant is a tool call -> tools_condition routes to tools
    # If the latest message (result) from assistant is a not a tool call -> tools_condition routes to END
    tools_condition,
)
builder.add_edge("tools", "assistant")

# The checkpointer lets the graph persist its state
memory = MemorySaver()
react_graph = builder.compile(checkpointer=memory)



def predict_react_agent_answer(example: dict):
    """Use this for answer evaluation"""

    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    messages = react_graph.invoke({"messages": ("user", example["input"])}, config)
    return {"response": messages["messages"][-1].content, "messages": messages}


async def retrieve_app_info_async(store, app_id):
    """
    Asynchronously retrieves app information based on the app_id.
    """

    try:
        app = await AppDetail.objects.filter(Q(appID=app_id) & Q(store__name=store)).select_related("developer", "genre", "store").afirst()
        app_detail = AppDetailSchema.from_orm(app)
        app_detail_dict = app_detail.dict()
        del app_detail_dict['developer']['slug']
        return app_detail_dict, app
    except Exception:
        return {"error": "App not found in the database."}


async def generate_response_async(messages, ai_conversation, conversation_limit):
    """
    Streams data asynchronously from the `llm.stream`.
    """
    try:
        ai_response = ""
        async for chunk in llm.astream(messages):
            ai_response += chunk.content
            
            yield "event: assistant\n"
            yield f"data: {json.dumps({'m': chunk.content})}\n\n"

        ai_conversation.conversation_data.append({
            'id': chunk.id,
            'type': 'assistant',
            'message': ai_response,
            'timestamp': str(timezone.now()),
        })
        ai_conversation.status = models.AiResponseStatus.COMPLETED
        ai_conversation.conversation_end = timezone.now()
        await sync_to_async(ai_conversation.save)()
        
    except Exception as e:
        conversation_limit.limit+=1
        await sync_to_async(conversation_limit.save)()
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


async def get_or_update_conversation_limit(user, start, end):
    return await sync_to_async(models.AiConversationLimit.objects.get_or_create)(
        user=user, timestamp__gte=start, timestamp__lt=end
    )


def create_error_response(error_message):
    return StreamingHttpResponse(
        f"event: error\ndata: {json.dumps({'error': error_message})}\n\n",
        content_type="text/event-stream; charset=utf-8",
    )


def is_valid_request(user_agent):
    return "curl" not in user_agent.lower()


def get_today_time_range():
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    return today_start, today_end


def prepare_messages(app_info, user_message):
    if "error" not in app_info:
        app_context = (
            "system",
            "You are an intelligent assistant specializing in providing detailed and accurate information about mobile applications. "
            "You can answer user queries regarding app details, such as the app's name, description, rating, developer, genre, installs, and other relevant features. "
            "Please provide concise, informative, and professional responses. If a user asks about something unrelated to apps, kindly inform them that you can only assist with app-related queries. "
            "If you do not have enough information to answer a specific question, let the user know politely and guide them to ask for app-related details."
            f"\nApp details:\n"
            f"Name: {app_info.get('name', 'Unknown')}\n"
            f"Description: {app_info.get('description', 'Unknown')}\n"
            f"Average Rating: {app_info.get('userAvgRating', 'Unknown')}\n"
            f"Developer: {app_info.get('developer', 'Unknown')}\n"
            f"Genre: {app_info.get('genre', 'Unknown')}\n"
            f"Installs: {app_info.get('installs', 'Unknown')}\n"
            f"Free: {app_info.get('free', 'Unknown')}\n"
            f"Contains Ads: {app_info.get('containsAds', 'Unknown')}\n"
            f"Offers In-App Purchases: {app_info.get('offersIAP', 'Unknown')}\n"
            f"Developer Website: {app_info.get('developerWebsite', 'Unknown')}\n"
            f"Developer Email: {app_info.get('developerEmail', 'Unknown')}\n"
            f"Privacy Policy: {app_info.get('privacyPolicy', 'Unknown')}\n"
            f"Developer Address: {app_info.get('developerAddress', 'Unknown')}\n"
            f"Released Date: {app_info.get('released', 'Unknown')}\n"
            f"Current Version: {app_info.get('currentVersion', 'Unknown')}\n"
            f"Current Version Released Date: {app_info.get('currentVersionDate', 'Unknown')}\n"
            f"Rating Distribution[1 star, 2 star, 3 star, 4 star, 5 star]: {app_info.get('histogram', 'Unknown')}\n"
            f"Application is Free: {app_info.get('free', 'Unknown')}\n"
            f"Is removed from store: {app_info.get('removed', 'Unknown')}\n"
            f"Total reviews: {app_info.get('reviews', 'Unknown')}\n"
            f"Is app support ad: {app_info.get('containsAds', 'Unknown')}\n"
            f"Daily installs: {app_info.get('downloads', 'Unknown')}\n"
        )
        return [app_context, ("human", user_message)]
    return [("system", app_info["error"]), ("human", user_message)]


async def get_or_create_ai_conversation(user, app_obj):
    return await sync_to_async(models.AiConversation.objects.get_or_create)(
        user=user,
        conversation_type=models.ConversationType.APP,
        app=app_obj,
    )


def update_ai_conversation(ai_conversation, message):
    ai_conversation.conversation_data.append(
        {
            'type': 'human',
            'message': message,
            'timestamp': str(timezone.now()),
        }
    )
    ai_conversation.status = models.AiResponseStatus.ONGOING
    ai_conversation.conversation_end = None
    sync_to_async(ai_conversation.save)()