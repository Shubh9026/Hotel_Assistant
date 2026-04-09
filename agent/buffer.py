from langchain_classic.memory import ConversationBufferMemory

# Clear memory on startup to avoid confusion
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

# Clear any existing memory
memory.clear()


def clear_memory():
    """Function to clear conversation memory if needed"""
    global memory
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )
    return "Memory cleared successfully"