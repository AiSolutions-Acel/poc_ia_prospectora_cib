from src.application.dto.chat_dto import ChatRequestDto, ChatResponseDto
from langchain_core.messages import HumanMessage

class ChatUseCase:
    def __init__(self, agent_executor):
        """
        agent_executor: Compilado de create_react_agent (StateGraph compiled)
        """
        self.agent_executor = agent_executor

    def execute(self, request: ChatRequestDto) -> ChatResponseDto:
        config = {"configurable": {"thread_id": request.session_id}}
        
        # Invoke the agent
        response_state = self.agent_executor.invoke(
            {"messages": [HumanMessage(content=request.message)]},
            config=config
        )
        
        # Extract the last message (the AI response)
        last_message = response_state["messages"][-1]
        
        return ChatResponseDto(
            answer=last_message.content,
            session_id=request.session_id
        )
