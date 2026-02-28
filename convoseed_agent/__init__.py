"""
ConvoSeed Agent — CSP-1 fingerprint encoder, identifier, and decoder.

The real implementation of the CSP-1 protocol for encoding conversational
style into portable .fp fingerprint files.

Quick start:
    from convoseed_agent import encode_conversation, identify, generate_with_prefix

Encode a conversation:
    from convoseed_agent import encode_conversation
    encode_conversation(messages, "identity.fp")

Identify a speaker:
    from convoseed_agent import identify
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    winner, scores = identify("some message", ["a.fp", "b.fp"], model)

Generate in someone's style:
    from convoseed_agent import generate_with_prefix, load_fp
    fp = load_fp("identity.fp")
    output = generate_with_prefix("Tell me about your weekend", fp)
"""

__version__ = "1.2.0"
__author__ = "Ashraful Islam"
__license__ = "MIT"

from convoseed_agent.encode import encode_conversation
from convoseed_agent.identify import identify, load_fp
from convoseed_agent.decode import generate_with_prefix, evaluate_similarity

__all__ = [
    "encode_conversation",
    "identify",
    "load_fp",
    "generate_with_prefix",
    "evaluate_similarity",
]
