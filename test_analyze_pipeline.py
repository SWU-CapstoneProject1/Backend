import json

from app.services.analyze_pipeline import analyze_terms_text


sample_terms = """
제1조(목적)
본 약관은 회사가 제공하는 서비스의 이용과 관련한 조건을 정합니다.

제2조(회사의 면책)
회사는 천재지변, 시스템 장애 또는 기타 불가항력적 사유로 인해 발생한 손해에 대하여 책임지지 않습니다.
회사는 회원에게 발생한 간접 손해에 대해 책임을 지지 않습니다.

제3조(약관의 변경)
회사는 필요하다고 판단하는 경우 사전 통지 없이 본 약관을 일방적으로 변경할 수 있습니다.

제4조(계약 해지)
회사는 회원이 약관을 위반한 경우 즉시 서비스 이용계약을 해지할 수 있습니다.

제5조(환불)
이미 결제된 금액은 어떠한 경우에도 환불되지 않습니다.
"""

result = analyze_terms_text(sample_terms)
print(json.dumps(result, ensure_ascii=False, indent=2))