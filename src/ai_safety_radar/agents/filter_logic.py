"""
ML-Security paper filtering logic inspired by N. Carlini's adversarial ML corpus.
Implements aggressive filtering to enforce 80/20 Pareto rule.

Reference: https://nicholas.carlini.com/writing/2019/advex_papers.json
"""
import re
from typing import Literal


class MLSecurityFilter:
    """
    Two-stage filter for AI Security papers:
    1. Kill List: Exclude pure cybersecurity/hardware/domain papers
    2. Anchor Requirement: Ambiguous terms need ML context to validate
    3. Strong Signals: Auto-accept obvious AML research
    """
    
    def __init__(self):
        # STAGE 1: Strong signals (always accept) - Adversarial ML core topics
        self.STRONG_AML = re.compile(r"""
            (?xi)\b(
            adversarial\s+(example|attack|perturb|training|robustness|patch)
            | prompt\s+inject\w* | jailbreak\w* | red[- ]?team\w*
            | model\s+extraction | model\s+inversion | membership\s+inference
            | machine\s+unlearning | alignment\s+tax | safety\s+fine[- ]?tun\w*
            | rlhf | constitutional\s+ai | reward\s+hack\w*
            | llm\s+attack | llm\s+security | llm\s+safety
            | ai\s+safety | ai\s+security | ai\s+alignment
            | backdoor\s+attack\w* | data\s+poison\w* | trojan\s+attack\w*
            | federated\s+learning\s+attack\w* | model\s+poison\w*
            | poison\w*\s+(attack|dataset|training)
            )\b
        """, re.VERBOSE)
        
        # STAGE 2: Ambiguous terms (need ML anchor to validate)
        self.AMBIGUOUS = re.compile(r"""
            (?xi)\b(
            trojan | backdoor | poison\w* | evasion | spoofing | fingerprint\w*
            | watermark\w* | steganograph\w* | perturbation | robust\w*
            )\b
        """, re.VERBOSE)
        
        # STAGE 3: ML anchors (validate ambiguous terms)
        self.ML_ANCHORS = re.compile(r"""
            (?xi)\b(
            neural\s+net\w* | transformer | llm | large\s+language\s+model
            | deep\s+learning | dnn | cnn | rnn | lstm | gpt | bert
            | diffusion\s+model | generative\s+model | classifier
            | dataset | training\s+(set|data) | gradient | weight | embedding
            | fine[- ]?tun\w* | prompt | token\w* | attention\s+mechanism
            | pre[- ]?train\w* | foundation\s+model | vision\s+model
            | machine\s+learn\w* | reinforcement\s+learn\w*
            )\b
        """, re.VERBOSE)
        
        # STAGE 4: Kill list (pure cybersecurity/hardware - auto-reject without ML context)
        self.KILL_LIST = re.compile(r"""
            (?xi)\b(
            # Hardware security (no ML)
            fpga | hardware\s+trojan | circuit\s+design | pcb | voltage\s+glitch
            | logic\s+gate | side[- ]?channel\s+power | differential\s+power\s+analysis
            
            # Traditional cybersecurity (no ML)
            | buffer\s+overflow | sql\s+inject\w* | cross[- ]?site | xss | csrf
            | ddos | man[- ]?in[- ]?the[- ]?middle | arp\s+spoofing | dns\s+poison
            | malware\s+analysis | ransomware | cve[- ]?\d{4} | exploit\s+kit
            | penetration\s+test | vulnerability\s+scan | firewall\s+rule
            
            # Pure cryptography (unless applied to ML)
            | elliptic\s+curve | rsa\s+encryption | aes\s+block | block\s+cipher
            | hash\s+collision | digital\s+signature\s+scheme
            
            # Domain-specific applications (not AI security research)
            | battery\s+(fault|diagnosis|monitor|manage)
            | medical\s+diagnosis | cancer\s+detection | tumor\s+segment
            | stock\s+(market|trad) | financial\s+forecast | portfolio\s+optim
            | robot\w*\s+navigation | autonomous\s+vehicle\s+control
            | weather\s+predict | climate\s+model | seismic\s+detect
            | protein\s+fold | drug\s+discover | molecule\s+gener
            )\b
        """, re.VERBOSE)
        
        # STAGE 5: LLM/GenAI boost (prioritize generative AI security)
        self.GENAI_BOOST = re.compile(r"""
            (?xi)\b(
            gpt[- ]?\d* | claude | llama[- ]?\d* | chatgpt | gemini | bard
            | mistral | mixtral | phi[- ]?\d | qwen | deepseek
            | generative\s+ai | language\s+model | diffusion\s+model
            | text[- ]?to[- ]?image | stable\s+diffusion | midjourney | dall[- ]?e
            | multimodal | vision[- ]?language | vlm
            )\b
        """, re.VERBOSE)
        
        # Safety/alignment specific terms (high priority)
        self.SAFETY_TERMS = re.compile(r"""
            (?xi)\b(
            alignment | misalignment | value\s+alignment
            | safety\s+eval | safety\s+bench | safety\s+audit
            | harmful\s+content | toxic\s+output | bias\s+detect
            | guardrail | content\s+filter | moderation
            | decepti\w+ | manipulat\w+ | persuasi\w+
            | existential\s+risk | x[- ]?risk | catastroph\w+
            )\b
        """, re.VERBOSE)
    
    def evaluate(self, title: str, abstract: str) -> dict:
        """
        Evaluate paper relevance using strict filtering logic.
        
        Returns:
            dict: {
                "status": "ACCEPT" | "REJECT",
                "score": float (0-100),
                "reasons": list[str],
                "confidence": float (0-1)
            }
        """
        text = f"{title} {abstract}".lower()
        score = 0
        reasons = []
        
        # CHECK 1: Kill list (auto-reject if no ML context)
        kill_matches = self.KILL_LIST.findall(text)
        ml_anchor_count = len(self.ML_ANCHORS.findall(text))
        
        if kill_matches and ml_anchor_count < 2:
            return {
                "status": "REJECT",
                "score": 0,
                "reasons": [f"KILL_LIST: {set(kill_matches)} (insufficient ML context)"],
                "confidence": 0.95
            }
        
        # CHECK 2: Strong AML signals (golden ticket)
        strong_matches = self.STRONG_AML.findall(text)
        if strong_matches:
            score += 50
            reasons.append(f"STRONG_AML: {set(strong_matches)}")
        
        # CHECK 3: Safety/alignment terms (high priority)
        safety_matches = self.SAFETY_TERMS.findall(text)
        if safety_matches:
            score += 30
            reasons.append(f"SAFETY_TERMS: {set(safety_matches)}")
        
        # CHECK 4: Ambiguous terms (require ML anchors)
        ambiguous_matches = self.AMBIGUOUS.findall(text)
        if ambiguous_matches:
            # Require at least 1 ML anchor to validate ambiguous terms
            if ml_anchor_count >= 1:
                score += 20 * min(len(ambiguous_matches), 3)
                reasons.append(f"VALIDATED_AMBIGUOUS: {set(ambiguous_matches)}")
            else:
                reasons.append(f"IGNORED_AMBIGUOUS: {set(ambiguous_matches)} (need ML context)")
        
        # CHECK 5: GenAI boost (prioritize LLM security)
        genai_matches = self.GENAI_BOOST.findall(text)
        if genai_matches:
            score = int(score * 1.3)
            reasons.append(f"GENAI_BOOST: {set(genai_matches)}")
        
        # CHECK 6: ML foundation (base relevance)
        if ml_anchor_count >= 3:
            score += 10
            reasons.append(f"ML_FOUNDATION: {ml_anchor_count} ML terms")
        
        # DECISION THRESHOLD (strict: need 50+ points for acceptance)
        confidence = min(score / 100, 0.99)
        status = "ACCEPT" if score >= 50 else "REJECT"
        
        return {
            "status": status,
            "score": round(score, 1),
            "reasons": reasons if reasons else ["NO_SIGNALS: No relevant terms found"],
            "confidence": round(confidence, 2)
        }
