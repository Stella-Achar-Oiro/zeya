"""
Run the generated pipeline in Open Chat Studio's own pipeline engine.

Needs an OCS checkout with its virtualenv and test database. Run it with
``make test-ocs-engine OCS_SOURCE=/path/to/open-chat-studio``. It is not part
of ``make test-ocs``.

The LLM provider is patched with OCS's FakeLlm, which records every call, so these
tests can assert that a danger-sign message never reaches an LLM.
"""

from unittest import mock

import pytest
from apps.pipelines.graph import PipelineGraph
from apps.pipelines.nodes.base import PipelineState
from apps.pipelines.repository import ORMRepository
from apps.utils.factories.experiment import ExperimentSessionFactory
from apps.utils.factories.pipelines import PipelineFactory
from apps.utils.factories.service_provider_factories import LlmProviderFactory, LlmProviderModelFactory
from apps.utils.langchain import build_fake_llm_service

from ocs.build_pipeline import SYSTEM_PROMPT_FILE, build_pipeline
from ocs.tests.danger_corpus import BILINGUAL_EXAMPLES

LLM_REPLY = "Eat a balanced diet, Mama."

REGISTERED = {
    "welcome_sent": True,
    "enrolled_at": "2026-09-01T09:00:00+00:00",
    "consent_given": True,
    "name": "Akinyi",
    "name_collected": True,
    "gestational_age_at_enrollment": 20,
    "registration_complete": True,
    "language_preference": "en",
    "study_group": "intervention",
}

DANGER_CASES = [
    (category, language, message)
    for category, languages in BILINGUAL_EXAMPLES.items()
    for language, message in languages.items()
]


@pytest.fixture()
def fake_llm():
    service = build_fake_llm_service(responses=[LLM_REPLY] * 5, token_counts=[0])
    service.llm.calls = []
    with mock.patch("apps.service_providers.models.LlmProvider.get_llm_service", return_value=service) as patched:
        yield service.llm, patched


@pytest.fixture()
def pipeline(db):
    provider = LlmProviderFactory.create()
    provider_model = LlmProviderModelFactory.create()
    pipeline = PipelineFactory.create()
    pipeline.data = build_pipeline(provider.id, provider_model.id)["data"]
    pipeline.save()
    pipeline.update_nodes_from_data()
    return pipeline


@pytest.fixture()
def run(pipeline):
    session = ExperimentSessionFactory.create()
    runnable = PipelineGraph.build_from_pipeline(pipeline).build_runnable()
    config = {"configurable": {"repo": ORMRepository(session=session)}}

    def _run(message: str, participant_data: dict) -> dict:
        state = PipelineState(messages=[message], experiment_session=session, participant_data=participant_data)
        return runnable.invoke(state, config=config)

    return _run


def _tags(output) -> list[str]:
    return [name for name, _category in output.get("output_message_tags", [])]


def test_pipeline_validates(pipeline):
    assert pipeline.validate() == {}


@pytest.mark.parametrize(("category", "language", "message"), DANGER_CASES)
def test_danger_message_never_reaches_llm(run, fake_llm, category, language, message):
    llm, get_llm_service = fake_llm

    output = run(message, REGISTERED | {"language_preference": language})

    reply = output["messages"][-1]
    assert reply.startswith("DHARURA:" if language == "sw" else "URGENT:")
    assert "Migori County Referral Hospital: 0800 723 253" in reply
    assert f"danger_sign:{category}" in _tags(output)
    assert "danger_router:EMERGENCY" in _tags(output)
    assert llm.calls == []
    get_llm_service.assert_not_called()


@pytest.mark.parametrize(("category", "language", "message"), DANGER_CASES[::3])
def test_danger_message_during_registration_gets_emergency(run, fake_llm, category, language, message):
    llm, _ = fake_llm

    output = run(message, {})

    assert output["messages"][-1].startswith("URGENT:")
    assert "registration:first_contact" not in _tags(output)
    assert llm.calls == []


def test_safe_message_from_registered_user_reaches_llm(run, fake_llm, caplog):
    llm, get_llm_service = fake_llm

    output = run("What should I eat?", REGISTERED)

    assert output["messages"][-1] == LLM_REPLY
    assert "danger_router:SAFE" in _tags(output)
    assert len(llm.calls) == 1
    messages = llm.get_call_messages()[0]
    system = messages[0].content
    assert system.startswith(SYSTEM_PROMPT_FILE.read_text())
    assert "User's current gestational age:" in system
    assert "Second trimester" in system
    human = messages[-1].content
    if not isinstance(human, str):  # OCS sends content blocks
        human = "".join(block["text"] for block in human if block.get("type") == "text")
    assert human == "What should I eat?"
    # Zeya called Gemini without a generation config, i.e. at the model's default temperature (1.0).
    assert "with parameters: {'temperature': 1.0}" in caplog.text


def test_safe_message_from_new_user_gets_welcome_without_llm(run, fake_llm):
    llm, _ = fake_llm

    output = run("Hello", {})

    assert output["messages"][-1].startswith("Welcome to the Antenatal Education Chatbot!")
    assert output["participant_data"]["welcome_sent"] is True
    assert llm.calls == []
