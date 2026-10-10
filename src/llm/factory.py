from typing import Any, List, Optional
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field
from src.config import settings


class MockChatModel(BaseChatModel):
    """Deterministic Mock LLM for offline tests and evaluation."""

    model_name: str = "mock-model"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        last_msg = messages[-1].content if messages else ""

        # Provide appropriate mock responses based on context
        if "profiler" in str(last_msg).lower() or "profile" in str(last_msg).lower():
            text = (
                "SEMANTIC_MAPPING:\n"
                "- CUST_LST_ADDR_ID_TX -> customer_id (Unique identifier for customer entity)\n"
                "- CUST_NAT_DOC_NUM_ID -> tax_id_cpf (National tax identifier, sensitive PII)\n"
                "- CUST_COMM_EML_ADDR_TX -> email (Customer email address, sensitive PII)\n"
                "- CUST_TEL_NUM_TX -> phone_number (Customer phone contact, sensitive PII)"
            )
        elif "fix" in str(last_msg).lower() or "diagnostic" in str(last_msg).lower():
            text = (
                "ROOT_CAUSE: Discrepancy caused by non-deterministic tie-breakers in window function and empty string vs null.\n"
                "ACTION: Add explicit secondary order column 'order_id' to ROW_NUMBER window, and use COALESCE(NULLIF(col, ''), 'DEFAULT')."
            )
        elif "steward" in str(last_msg).lower() or "catalog" in str(last_msg).lower():
            text = (
                "DOCUMENTATION:\n"
                "Table migrated successfully to Delta Lake Medallion format with strict mathematical reconciliation."
            )
        else:
            text = "Generated migration code compliant with Databricks Delta Lake standards."

        generation = ChatGeneration(message=AIMessage(content=text))
        return ChatResult(generations=[generation])

    @property
    def _llm_type(self) -> str:
        return "mock"


def get_chat_model(provider: Optional[str] = None) -> BaseChatModel:
    """Returns the configured LLM instance or fallback to MockChatModel."""
    prov = (provider or settings.llm.provider).lower()

    if prov == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=settings.llm.model_name or "gemini-2.5-flash",
                temperature=settings.llm.temperature,
            )
        except Exception:
            return MockChatModel()

    elif prov == "openai":
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model_name=settings.llm.model_name or "gpt-4o",
                temperature=settings.llm.temperature,
            )
        except Exception:
            return MockChatModel()

    elif prov == "ollama":
        try:
            try:
                from langchain_ollama import ChatOllama
            except ImportError:
                from langchain_community.chat_models import ChatOllama
            return ChatOllama(
                base_url=settings.llm.ollama_base_url,
                model=settings.llm.model_name or "llama3.2:latest",
                temperature=settings.llm.temperature,
            )
        except Exception:
            return MockChatModel()

    return MockChatModel()
