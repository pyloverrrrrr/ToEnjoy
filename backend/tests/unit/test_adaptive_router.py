from app.core.rag.adaptive_router import AdaptiveRouter, SearchStrategy


class TestAdaptiveRouter:
    def test_patient_routes_to_kb_patient(self):
        router = AdaptiveRouter()
        decision = router.route(role="patient", sub_queries=[])
        assert decision.kb_collection == "kb_patient"

    def test_doctor_routes_to_kb_professional(self):
        router = AdaptiveRouter()
        decision = router.route(role="doctor", sub_queries=[])
        assert decision.kb_collection == "kb_professional"

    def test_single_query_uses_direct_strategy(self):
        router = AdaptiveRouter()
        decision = router.route(role="patient", sub_queries=[])
        assert decision.strategy == SearchStrategy.DIRECT

    def test_multiple_sub_queries_uses_self_rag_strategy(self):
        router = AdaptiveRouter()
        decision = router.route(role="doctor", sub_queries=["q1", "q2"])
        assert decision.strategy == SearchStrategy.SELF_RAG

    def test_exactly_two_sub_queries_is_self_rag(self):
        router = AdaptiveRouter()
        decision = router.route(role="patient", sub_queries=["a", "b"])
        assert decision.strategy == SearchStrategy.SELF_RAG
