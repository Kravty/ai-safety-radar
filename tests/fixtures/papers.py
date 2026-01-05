def load_fixture(name: str) -> dict:
    """Load test paper fixtures"""
    fixtures = {
        "gcg_jailbreak.json": {
            "title": "Universal Jailbreak via Gradient-Based Suffix Optimization",
            "content": "Abstract: We introduce GCG, an automated method for generating adversarial suffixes that cause LLMs to bypass alignment. Our method achieves 99% success rate on Llama-2 and GPT-3.5. We demonstrate that these attacks transfer to other models.",
            "url": "http://arxiv.org/abs/2307.15043",
            "published_date": "2023-07-28",
            "source": "arxiv",
            "id": "2307.15043",
            "metadata": {"authors": ["Andy Zou", "Zifan Wang"]}
        },
        "adagres_rag.json": {
            "title": "AdaGReS: Adaptive Greedy Context Selection",
            "content": "Abstract: We present AdaGReS for efficient retrieval in RAG systems. It optimizes context selection to reduce token usage while maintaining performance. This is purely an efficiency improvement.",
            "url": "http://arxiv.org/abs/2512.25052",
            "published_date": "2025-12-31",
            "source": "arxiv", 
            "id": "2512.25052",
            "metadata": {"authors": ["Researcher One"]}
        },
        "adversarial_training_defense.json": {
            "title": "Certifying Robustness via Adversarial Training",
            "content": "Abstract: We propose a new adversarial training method that provides certified robustness guarantees against L-infinity attacks. Our method improves state-of-the-art certified accuracy by 5%.",
            "url": "http://arxiv.org/abs/def.123",
            "published_date": "2025-01-01",
            "source": "arxiv",
            "id": "def.123",
            "metadata": {}
        },
        "benign_optimization.json": {
            "title": "Faster Matrix Multiplication",
            "content": "Abstract: We optimize matrix multiplication kernels for GPU. 10% faster. No security implications.",
            "url": "http://arxiv.org/abs/opt.123",
            "published_date": "2025-01-01",
            "source": "arxiv",
            "id": "opt.123",
            "metadata": {}
        }
    }
    return fixtures.get(name, {})
