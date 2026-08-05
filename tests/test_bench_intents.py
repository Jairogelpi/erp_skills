from erp_agent_os.bench_intents import INTENTS
from erp_agent_os.catalog import CATALOG_BY_ID


def test_exactly_24_intents():
    assert len(INTENTS) == 24


def test_intent_ids_are_unique():
    ids = [intent.intent_id for intent in INTENTS]
    assert len(ids) == len(set(ids))


def test_every_intent_references_a_cataloged_skill():
    for intent in INTENTS:
        assert intent.skill_id in CATALOG_BY_ID


def test_two_intents_per_skill():
    counts: dict[str, int] = {}
    for intent in INTENTS:
        counts[intent.skill_id] = counts.get(intent.skill_id, 0) + 1
    assert set(counts.values()) == {2}


def test_template_renders_with_required_field_pool_values():
    for intent in INTENTS:
        values = {
            field: intent.field_pool(field)[0] for field in intent.required_fields
        }
        rendered = intent.template.format(**values)
        assert "{" not in rendered
