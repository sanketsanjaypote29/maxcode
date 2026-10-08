import logging


class _GoogleGenAISchemaWarningFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        ignored_messages = {
            "Key 'additionalProperties' is not supported in schema, ignoring",
            "Key '$schema' is not supported in schema, ignoring",
        }
        return not (
            record.name == "langchain_google_genai._function_utils"
            and record.levelno == logging.WARNING
            and record.getMessage() in ignored_messages
        )


#Set root logger to WARNIG - suppresses noisy third-party library logs (OpenAI)
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logging.getLogger("langchain_google_genai._function_utils").addFilter(
    _GoogleGenAISchemaWarningFilter()
)


def get_logger(name: str) -> logging.Logger:
    #Our own loggers run at DEBUG - only third party libraries are suppressed
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    return logger