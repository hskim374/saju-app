"""Daily fortune calculation from a target solar date."""

from __future__ import annotations

from datetime import date

from data.branches import BRANCHES_BY_KOR
from data.day_pillar_sentences import DAY_PILLAR_SENTENCES
from data.stems import STEMS_BY_KOR
from services.analysis_sentence_store import load_analysis_sentences
from services.interpretation_engine import build_daily_section
from services.report_display import format_stem_label
from services.saju_calculator import get_day_pillar_for_solar_date
from services.ten_gods import calculate_ten_god_for_stem, calculate_ten_gods

DAILY_RULES = {
    "비견": {
        "headline": "주도적으로 움직이되 고집은 줄이는 편이 좋은 날입니다.",
        "summary": "주도적으로 움직이되 고집은 줄이는 편이 좋은 날입니다.",
        "explanation": "내 판단이 앞에 서기 쉬워 빠르게 결정할 수 있지만, 주변 조율을 빼먹기 쉬운 흐름입니다.",
        "advice": "결정을 내리기 전 상대 일정과 조건을 한 번 더 확인하는 편이 좋습니다.",
        "keywords": ["주도", "균형", "협업"],
    },
    "겁재": {
        "headline": "경쟁심이 올라오기 쉬워 지출과 관계를 함께 점검하는 것이 좋습니다.",
        "summary": "경쟁심이 올라오기 쉬워 지출과 관계를 함께 점검하는 것이 좋습니다.",
        "explanation": "사람과 일의 자극이 강해져 감정과 지출이 생각보다 쉽게 커질 수 있습니다.",
        "advice": "승부를 빨리 보려 하지 말고 오늘 쓸 힘과 돈의 한도를 먼저 정해 두는 편이 좋습니다.",
        "keywords": ["주의", "경쟁", "분산"],
    },
    "식신": {
        "headline": "실무와 생산성을 차분히 끌어올리기 좋은 날입니다.",
        "summary": "실무와 생산성을 차분히 끌어올리기 좋은 날입니다.",
        "explanation": "손에 잡히는 결과를 만들기 좋은 날이라 미뤄 둔 일을 정리하기에 적합합니다.",
        "advice": "작은 결과라도 눈에 보이게 마무리하면 하루 흐름이 훨씬 안정됩니다.",
        "keywords": ["성과", "실행", "안정"],
    },
    "상관": {
        "headline": "의사결정은 신중하게 하고 말의 강약을 조절하는 편이 좋습니다.",
        "summary": "의사결정은 신중하게 하고 말의 강약을 조절하는 편이 좋습니다.",
        "explanation": "표현력이 살아나는 대신 강한 말과 빠른 결론이 마찰을 만들 수 있는 날입니다.",
        "advice": "중요한 말과 메시지는 한 번 다듬고 보내는 편이 안전합니다.",
        "keywords": ["주의", "문서", "표현"],
    },
    "편재": {
        "headline": "사람과 기회를 넓히기 좋은 날이지만 선택은 선별적으로 하는 편이 좋습니다.",
        "summary": "사람과 기회를 넓히기 좋은 날이지만 선택은 선별적으로 하는 편이 좋습니다.",
        "explanation": "바깥 제안과 접점이 늘기 쉬워 기회는 보이지만 집중이 흩어질 수 있습니다.",
        "advice": "잡을 일 한두 개만 정하고 나머지는 메모로 넘기는 편이 좋습니다.",
        "keywords": ["기회", "대외활동", "선별"],
    },
    "정재": {
        "headline": "재정과 일정 관리를 정리하기 좋은 날입니다.",
        "summary": "재정과 일정 관리를 정리하기 좋은 날입니다.",
        "explanation": "실무와 생활 기준을 정리할수록 바로 체감되는 안정감이 생기기 쉬운 날입니다.",
        "advice": "결제, 일정, 해야 할 일을 한 번에 정리하면 하루가 훨씬 가벼워집니다.",
        "keywords": ["축적", "관리", "실무"],
    },
    "편관": {
        "headline": "압박이 생겨도 원칙을 유지하면 흐름을 잡기 좋은 날입니다.",
        "summary": "압박이 생겨도 원칙을 유지하면 흐름을 잡기 좋은 날입니다.",
        "explanation": "긴장감이 올라와도 기준을 놓치지 않으면 오히려 정리가 빨라질 수 있습니다.",
        "advice": "무리하게 버티기보다 중요한 일부터 순서대로 줄이는 편이 좋습니다.",
        "keywords": ["긴장", "원칙", "대응"],
    },
    "정관": {
        "headline": "책임감과 신뢰가 드러나기 쉬운 날입니다.",
        "summary": "책임감과 신뢰가 드러나기 쉬운 날입니다.",
        "explanation": "해야 할 일을 분명히 처리할수록 평판과 신뢰가 바로 남기 쉬운 흐름입니다.",
        "advice": "작은 약속이라도 정확히 지키는 편이 오늘 운을 살립니다.",
        "keywords": ["책임", "평가", "신뢰"],
    },
    "편인": {
        "headline": "관점을 바꾸고 정보를 탐색하기 좋은 날입니다.",
        "summary": "관점을 바꾸고 정보를 탐색하기 좋은 날입니다.",
        "explanation": "익숙한 답보다 다른 해석이 더 잘 보일 수 있어 탐색과 비교에 강점이 있습니다.",
        "advice": "새 선택지를 보더라도 바로 옮기기보다 시험해 보는 수준으로 다루는 편이 좋습니다.",
        "keywords": ["탐색", "전환", "통찰"],
    },
    "정인": {
        "headline": "배움과 정리에 집중하면 안정감이 살아나는 날입니다.",
        "summary": "배움과 정리에 집중하면 안정감이 살아나는 날입니다.",
        "explanation": "준비와 정리, 자료 축적이 실제 안정감으로 이어지기 쉬운 하루입니다.",
        "advice": "새 일을 늘리기보다 공부와 정리 시간을 확보하는 편이 좋습니다.",
        "keywords": ["학습", "정리", "안정"],
    },
}

DAY_STEM_DAILY_LINES = {
    "갑": "원국 일간이 갑목이면 오늘처럼 자극이 들어와도 먼저 방향이 맞는지부터 점검하는 편입니다.",
    "을": "원국 일간이 을목이면 오늘 생긴 변수도 정면 돌파보다 부드러운 조정으로 풀어 가는 편입니다.",
    "병": "원국 일간이 병화이면 오늘 컨디션이 붙을 때 반응 속도와 표현 강도가 함께 올라오기 쉽습니다.",
    "정": "원국 일간이 정화이면 오늘 일도 바로 결론을 내리기보다 분위기와 상대 반응을 함께 살피는 편입니다.",
    "무": "원국 일간이 무토이면 오늘 자극도 버틸 수 있는지부터 따져 보며 현실성을 먼저 확인하는 편입니다.",
    "기": "원국 일간이 기토이면 오늘 일정도 사람과 조건을 같이 보며 무리가 덜한 방식으로 정리하는 편입니다.",
    "경": "원국 일간이 경금이면 오늘처럼 판단이 필요한 날에는 기준부터 세우고 결론을 분명히 하려는 편입니다.",
    "신": "원국 일간이 신금이면 오늘 작은 차이와 디테일에 민감해져 결과 품질을 더 세밀하게 챙기기 쉽습니다.",
    "임": "원국 일간이 임수이면 오늘 일도 눈앞의 반응보다 전체 흐름과 다음 수순을 함께 보며 판단하는 편입니다.",
    "계": "원국 일간이 계수이면 오늘 들어온 자극도 겉말보다 숨은 맥락과 분위기를 읽으며 받아들이는 편입니다.",
}

MONTH_BRANCH_DAILY_LINES = {
    "자": "월지가 자수라 오늘 판단에서도 먼저 정보를 모으고 흐름을 읽어야 마음이 놓이는 편입니다.",
    "축": "월지가 축토라 오늘 일정도 속도보다 버틸 수 있는 틀을 먼저 세워야 안정감이 생기는 편입니다.",
    "인": "월지가 인목이라 오늘은 가만히 유지하기보다 새로운 방향을 직접 열어 보려는 마음이 올라올 수 있습니다.",
    "묘": "월지가 묘목이라 오늘도 정면 충돌보다 부드럽게 조율하면서 판을 넓히는 방식이 더 잘 맞습니다.",
    "진": "월지가 진토라 오늘 할 일도 여러 조건을 한꺼번에 묶어 현실적으로 정리하는 편이 더 자연스럽습니다.",
    "사": "월지가 사화라 오늘은 반응 속도가 평소보다 빨라지고 존재감도 자연스럽게 커질 가능성이 있습니다.",
    "오": "월지가 오화라 오늘 정적인 흐름보다 움직이고 드러나는 자리에서 에너지가 더 잘 붙을 수 있습니다.",
    "미": "월지가 미토라 오늘도 서두른 변화보다 오래 갈 수 있는 방식인지부터 확인하는 편이 더 맞습니다.",
    "신": "월지가 신금이라 오늘 일정에서는 정리, 마감, 우선순위 설정이 실제 체감 차이를 만들기 쉽습니다.",
    "유": "월지가 유금이라 오늘은 작은 실수와 디테일 차이를 먼저 잡아내는 쪽에서 강점이 더 잘 드러납니다.",
    "술": "월지가 술토라 오늘 맡은 일도 책임과 기준이 분명할수록 훨씬 안정적으로 풀리기 쉽습니다.",
    "해": "월지가 해수라 오늘은 바로 확정하기보다 여지를 남기고 흐름을 조금 더 보는 편이 자연스럽습니다.",
}

DAY_BRANCH_CONTEXT_LINES = {
    "자": "오늘 일지에 자수가 들어오면 생각이 길어지기 쉬워 말보다 관찰이 먼저 나올 수 있습니다.",
    "축": "오늘 일지에 축토가 들어오면 속도를 줄이고 현실적인 범위를 다시 정리하는 쪽으로 기울기 쉽습니다.",
    "인": "오늘 일지에 인목이 들어오면 정체된 일보다 새 방향과 확장 이슈가 눈에 더 잘 들어올 수 있습니다.",
    "묘": "오늘 일지에 묘목이 들어오면 사람과 일정 사이의 거리 조절이 생각보다 중요한 포인트가 될 수 있습니다.",
    "진": "오늘 일지에 진토가 들어오면 복잡한 일도 묶어서 정리하려는 힘이 올라올 가능성이 큽니다.",
    "사": "오늘 일지에 사화가 들어오면 반응이 빨라지는 대신 말의 강약도 함께 커질 수 있습니다.",
    "오": "오늘 일지에 오화가 들어오면 존재감과 표현 욕구가 올라와 움직이는 일이 더 눈에 띄기 쉽습니다.",
    "미": "오늘 일지에 미토가 들어오면 겉으로 조용해 보여도 속에서는 유지 가능성을 더 오래 따질 가능성이 큽니다.",
    "신": "오늘 일지에 신금이 들어오면 기준이 흐린 상태를 오래 두기보다 깔끔하게 정리하려는 힘이 생기기 쉽습니다.",
    "유": "오늘 일지에 유금이 들어오면 결과물의 완성도와 정돈 상태를 특히 민감하게 보게 될 수 있습니다.",
    "술": "오늘 일지에 술토가 들어오면 책임감이 먼저 올라와 작은 약속도 가볍게 넘기기 어려울 수 있습니다.",
    "해": "오늘 일지에 해수가 들어오면 단정 짓기보다 여러 가능성을 더 길게 살피는 흐름이 강해질 수 있습니다.",
}

DAILY_STRENGTH_LINES = {
    "비견": "오늘은 내 페이스를 잡는 힘이 살아 있어 흐름만 잘 정리하면 주도권을 가져오기 좋습니다.",
    "겁재": "오늘은 자극이 강하지만 경계만 잘 세우면 관계와 돈 모두에서 실수를 줄이기 좋습니다.",
    "식신": "오늘은 손에 잡히는 결과물을 남길 힘이 있어 작은 마감도 성과로 체감되기 쉽습니다.",
    "상관": "오늘은 표현력과 문제 인식이 살아 있어 답답한 지점을 빨리 짚어낼 수 있습니다.",
    "편재": "오늘은 바깥 기회와 접점을 읽는 감각이 살아 있어 필요한 연결을 만들기 좋습니다.",
    "정재": "오늘은 생활과 실무 기준을 정리하는 힘이 살아 있어 바로 체감되는 안정감을 만들기 좋습니다.",
    "편관": "오늘은 긴장 속에서도 우선순위를 세우면 오히려 흐름을 빠르게 정리할 수 있습니다.",
    "정관": "오늘은 책임감과 신뢰가 드러나기 쉬워 작은 약속도 평판으로 남기 좋습니다.",
    "편인": "오늘은 다른 시각을 보는 힘이 살아 있어 막힌 문제의 우회로를 찾기 좋습니다.",
    "정인": "오늘은 자료 정리와 학습을 붙이면 마음이 안정되고 판단도 또렷해지기 쉽습니다.",
}

DAILY_RISK_LINES = {
    "비견": "오늘은 내 판단이 앞서기 쉬워 조율 단계를 건너뛰면 작은 충돌이 남을 수 있습니다.",
    "겁재": "오늘은 경쟁심이 올라오면 지출과 감정 소모가 함께 커질 수 있습니다.",
    "식신": "오늘은 눈앞 결과에만 집중하면 더 중요한 우선순위를 놓칠 수 있습니다.",
    "상관": "오늘은 맞는 말을 하더라도 수위가 세지면 관계 피로가 남을 수 있습니다.",
    "편재": "오늘은 제안이 많아 보여도 다 잡으려 하면 집중이 쉽게 흩어질 수 있습니다.",
    "정재": "오늘은 정리에만 오래 머물면 결정 시점을 놓칠 수 있습니다.",
    "편관": "오늘은 압박에 반응해 무리하게 버티면 체력과 집중력이 함께 꺾일 수 있습니다.",
    "정관": "오늘은 책임감이 과하게 올라오면 남의 몫까지 떠안아 피로가 커질 수 있습니다.",
    "편인": "오늘은 탐색이 길어지면 실행이 늦어질 수 있어 시험 범위를 좁히는 편이 좋습니다.",
    "정인": "오늘은 준비가 길어질수록 실제 움직임이 늦어질 수 있습니다.",
}

DAILY_PROFILE_HEADLINES = {
    "planner": "오늘은 방향부터 정리해야 체감이 분명해지는 날입니다.",
    "connector": "오늘은 사람과 조건을 함께 보며 조율해야 결과가 남는 날입니다.",
    "driver": "오늘은 속도는 붙지만 강약 조절이 함께 필요한 날입니다.",
    "stabilizer": "오늘은 무리한 확장보다 버틸 수 있는 틀을 먼저 세워야 하는 날입니다.",
    "precision": "오늘은 디테일과 마감 기준이 하루의 품질을 좌우하는 날입니다.",
    "observer": "오늘은 바로 결론보다 흐름을 읽는 판단이 더 중요해지는 날입니다.",
}

DAILY_PROFILE_EXPLANATIONS = {
    "planner": "원국의 판단 축이 방향과 우선순위를 먼저 세우는 쪽에 있어, 오늘도 무엇을 먼저 할지 정하는 순간 흐름이 안정되기 쉽습니다.",
    "connector": "원국에서는 사람과 조건을 같이 보는 힘이 강해, 오늘도 단독 판단보다 조율이 붙을 때 결과가 더 자연스럽게 이어질 수 있습니다.",
    "driver": "원국에서는 반응과 실행이 빠르게 올라오는 편이라, 오늘도 속도는 강점이지만 열기를 어떻게 조절하느냐가 함께 중요해집니다.",
    "stabilizer": "원국의 기본 결이 현실성과 유지 가능성을 먼저 보기 때문에, 오늘도 무리한 시도보다 오래 갈 수 있는 방식이 더 잘 맞습니다.",
    "precision": "원국에서는 작은 차이와 완성도를 오래 보는 힘이 살아 있어, 오늘도 마감 기준과 세부 정리가 결과를 바꾸기 쉽습니다.",
    "observer": "원국에서는 눈앞 반응보다 전체 맥락을 읽는 힘이 커서, 오늘도 한 템포 늦춘 판단이 오히려 더 정확할 수 있습니다.",
}

DAILY_PROFILE_ADVICE = {
    "planner": "오늘은 해야 할 순서를 세 줄로 적어 두고 그 안에서만 움직이는 편이 좋습니다.",
    "connector": "오늘은 혼자 결론 내리기보다 관련된 사람 한 명의 조건을 더 확인하는 편이 좋습니다.",
    "driver": "오늘은 반응 속도를 살리되 바로 확정하지 말고 한 번만 더 다듬는 편이 좋습니다.",
    "stabilizer": "오늘은 새 일을 벌이기보다 현재 일을 정리하고 버틸 수 있는 범위를 먼저 확인하는 편이 좋습니다.",
    "precision": "오늘은 시작보다 끝내는 기준을 먼저 정해 두는 편이 하루 피로를 줄이는 데 도움이 됩니다.",
    "observer": "오늘은 큰 판단을 바로 내리기보다 저녁까지 한 번 더 흐름을 보는 편이 안전합니다.",
}

DAY_STEM_HEADLINE_LINES = {
    "갑": "방향을 먼저 정할수록 판단이 빨라지는 날입니다.",
    "을": "조율과 완급 조절이 결과 차이를 만드는 날입니다.",
    "병": "속도는 붙지만 열기를 어떻게 다루느냐가 중요한 날입니다.",
    "정": "분위기와 말의 순서를 살펴야 흐름이 매끄러운 날입니다.",
    "무": "현실성 검토가 하루의 품질을 좌우하는 날입니다.",
    "기": "사람과 조건을 함께 봐야 흔들림이 줄어드는 날입니다.",
    "경": "기준과 결론을 선명하게 잡을수록 편한 날입니다.",
    "신": "디테일과 마감 감각이 결과 차이를 만드는 날입니다.",
    "임": "큰 맥락을 보고 움직여야 손실이 줄어드는 날입니다.",
    "계": "겉말보다 숨은 분위기를 읽을수록 안전한 날입니다.",
}

MONTH_BRANCH_HEADLINE_LINES = {
    "자": "정보를 먼저 정리하면 판단 피로가 줄어듭니다.",
    "축": "버틸 수 있는 범위를 먼저 정하는 편이 좋습니다.",
    "인": "새 방향을 빨리 넓히기보다 우선순위부터 고정하는 편이 낫습니다.",
    "묘": "사람과 일정 사이의 거리 조절이 특히 중요합니다.",
    "진": "한꺼번에 여러 일을 묶어 정리하려는 힘이 강해집니다.",
    "사": "반응 속도는 빠르지만 표현 수위를 조절하는 편이 안전합니다.",
    "오": "움직임이 많은 자리일수록 속도 조절이 더 중요합니다.",
    "미": "유지 가능한 방식인지 먼저 확인해야 체감이 안정됩니다.",
    "신": "정리와 마감 기준을 먼저 세우면 훨씬 수월합니다.",
    "유": "작은 차이와 실수를 먼저 잡아내면 전체 흐름이 깔끔해집니다.",
    "술": "책임이 걸린 약속일수록 더 무겁게 느껴질 수 있습니다.",
    "해": "바로 결론 내리기보다 여지를 남겨두는 편이 더 맞습니다.",
}

DAY_STEM_DAILY_STRENGTHS = {
    "갑": "오늘은 방향만 선명하게 잡으면 밀어붙이는 힘이 빠르게 붙을 수 있습니다.",
    "을": "오늘은 상대 반응을 읽으며 조정하는 감각이 살아 있어 불필요한 마찰을 줄이기 좋습니다.",
    "병": "오늘은 분위기를 끌어올리고 일을 움직이게 만드는 추진력이 붙기 쉽습니다.",
    "정": "오늘은 필요한 말만 골라 전달하는 힘이 살아 있어 관계 피로를 줄이기 좋습니다.",
    "무": "오늘은 흔들리는 조건 속에서도 중심을 잡고 현실 판단을 유지하기 좋습니다.",
    "기": "오늘은 복잡한 상황도 사람과 조건을 함께 엮어 무리 없는 답을 찾기 좋습니다.",
    "경": "오늘은 기준만 정해지면 결론을 빠르게 정리하고 마감까지 끌고 가기 쉽습니다.",
    "신": "오늘은 디테일과 완성도를 챙기는 힘이 살아 있어 결과 품질을 높이기 좋습니다.",
    "임": "오늘은 큰 흐름과 다음 수순을 같이 읽는 감각이 살아 있어 성급한 선택을 줄이기 좋습니다.",
    "계": "오늘은 겉으로 드러난 말보다 맥락을 읽는 힘이 살아 있어 오판을 줄이기 좋습니다.",
}

DAY_STEM_DAILY_RISKS = {
    "갑": "오늘은 방향을 넓게 보기만 하다가 정작 첫 실행 시점을 놓칠 수 있습니다.",
    "을": "오늘은 지나친 조율이 결론을 늦춰 타이밍을 흐릴 수 있습니다.",
    "병": "오늘은 속도가 붙을수록 말과 반응이 과해질 가능성을 함께 조심해야 합니다.",
    "정": "오늘은 분위기를 오래 보다가 이미 정해 둔 결론을 밖으로 내는 시점이 늦어질 수 있습니다.",
    "무": "오늘은 안전성 검토가 길어지면 움직임 자체가 늦어질 수 있습니다.",
    "기": "오늘은 모두를 맞추려는 마음이 강해질수록 내 우선순위가 흐려질 수 있습니다.",
    "경": "오늘은 기준을 빨리 세우는 힘이 장점이지만, 유연성이 떨어지면 충돌이 남을 수 있습니다.",
    "신": "오늘은 디테일을 오래 보다가 큰 순서를 놓칠 수 있습니다.",
    "임": "오늘은 큰 그림을 오래 보다 보니 눈앞 마감과 즉시 대응이 느려질 수 있습니다.",
    "계": "오늘은 맥락을 너무 오래 읽다 보면 간단히 끝낼 문제도 길어질 수 있습니다.",
}

MONTH_BRANCH_DAILY_STRENGTHS = {
    "자": "오늘은 정보를 빠르게 연결해 판단의 빈칸을 메우는 힘이 좋습니다.",
    "축": "오늘은 생활과 일정의 기본 틀을 다시 세우면 금방 안정감을 되찾기 쉽습니다.",
    "인": "오늘은 새로운 방향을 보더라도 중심축을 잃지 않고 움직일 여지가 있습니다.",
    "묘": "오늘은 사람과 사람 사이의 거리를 부드럽게 조절하는 능력이 잘 드러납니다.",
    "진": "오늘은 복잡한 문제를 한 번에 묶어 정리하는 감각이 강하게 살아날 수 있습니다.",
    "사": "오늘은 반응과 실행이 빨라 필요한 타이밍을 붙잡기 쉬운 날입니다.",
    "오": "오늘은 존재감과 추진력이 살아 있어 흐름을 직접 움직이기 좋습니다.",
    "미": "오늘은 조용히 다져도 오래 가는 선택을 골라내는 힘이 있습니다.",
    "신": "오늘은 정리와 마감 능력이 살아 있어 흩어진 일을 수습하기 좋습니다.",
    "유": "오늘은 작은 실수와 미세한 차이를 먼저 잡아 결과 품질을 높이기 좋습니다.",
    "술": "오늘은 책임이 걸린 일에서 버티는 힘과 기준 유지력이 잘 드러날 수 있습니다.",
    "해": "오늘은 서두르지 않고 흐름을 읽는 힘 덕분에 판단 실수를 줄이기 좋습니다.",
}

MONTH_BRANCH_DAILY_RISKS = {
    "자": "오늘은 정보가 많아질수록 결론을 내리는 시점이 늦어질 수 있습니다.",
    "축": "오늘은 안정부터 잡으려다 기회 대응 속도가 느려질 수 있습니다.",
    "인": "오늘은 새 방향이 많아 보일수록 에너지가 여러 갈래로 분산될 수 있습니다.",
    "묘": "오늘은 조율을 오래 하다 보면 정작 내 결론이 뒤로 밀릴 수 있습니다.",
    "진": "오늘은 한꺼번에 다 정리하려는 마음이 커지면 피로가 빨리 쌓일 수 있습니다.",
    "사": "오늘은 반응이 빠른 만큼 말의 수위가 세지지 않도록 조절이 필요합니다.",
    "오": "오늘은 에너지가 강해질수록 지나친 속도와 과열을 조심해야 합니다.",
    "미": "오늘은 유지 가능성만 오래 보다가 실행 타이밍을 놓칠 수 있습니다.",
    "신": "오늘은 기준을 선명히 세우는 힘이 강해질수록 융통성이 줄어들 수 있습니다.",
    "유": "오늘은 디테일을 오래 만지다가 정작 마감 시점을 놓칠 수 있습니다.",
    "술": "오늘은 책임감이 과해지면 남의 몫까지 떠안아 피로가 커질 수 있습니다.",
    "해": "오늘은 여지를 너무 많이 남기면 결론이 흐릿해질 수 있습니다.",
}

MONTH_BRANCH_DAILY_ACTIONS = {
    "자": "오늘은 정보를 바로 쌓기보다 핵심 두세 개만 남기고 나머지는 과감히 넘기는 편이 좋습니다.",
    "축": "오늘은 할 일 상한선을 먼저 정하고 그 안에서만 움직이는 편이 더 안정적입니다.",
    "인": "오늘은 새 방향이 보여도 하나만 고르고 나머지는 다음 순서로 미루는 편이 좋습니다.",
    "묘": "오늘은 사람과 일정 사이의 간격을 여유 있게 잡아야 흐름이 부드럽습니다.",
    "진": "오늘은 복잡한 일도 한 번에 다 처리하려 하지 말고 묶음 하나씩 끊어 가는 편이 좋습니다.",
    "사": "오늘은 반응 속도는 살리되 말의 강약을 미리 조절해 두는 편이 좋습니다.",
    "오": "오늘은 에너지가 붙더라도 속도보다 끝내는 순서를 먼저 정하는 편이 낫습니다.",
    "미": "오늘은 오래 갈 수 있는지부터 확인한 뒤 움직이는 편이 결과를 남기기 쉽습니다.",
    "신": "오늘은 마감 기준을 먼저 적어 두면 흐트러짐 없이 끝내기 쉽습니다.",
    "유": "오늘은 디테일을 챙기되 멈출 시점도 같이 정해야 피로가 덜합니다.",
    "술": "오늘은 책임이 걸린 일부터 순서대로 끊어 처리하는 편이 좋습니다.",
    "해": "오늘은 결론을 밀어붙이기보다 저녁쯤 한 번 더 보며 정하는 편이 안전합니다.",
}

TIME_BRANCH_DAILY_ACTIONS = {
    "자": "혼자 정리하는 시간을 짧게라도 확보해야 생각이 흩어지지 않습니다.",
    "축": "감정이 올라와도 바로 반응하지 말고 안에서 한 번 정리한 뒤 움직이는 편이 좋습니다.",
    "인": "새 아이디어가 보여도 오늘은 하나만 시험해 보는 편이 좋습니다.",
    "묘": "사람과의 간격을 무리하게 좁히지 말고 편한 거리부터 맞추는 편이 좋습니다.",
    "진": "여러 선택지를 동시에 쥐기보다 가장 현실적인 한 가지부터 정리하는 편이 좋습니다.",
    "사": "빠른 반응이 필요한 날이지만 말의 강약은 한 번 더 점검하는 편이 좋습니다.",
    "오": "에너지가 붙어도 속도만 믿지 말고 마감 순서를 먼저 잡는 편이 좋습니다.",
    "미": "가까운 일일수록 오래 갈 수 있는지부터 확인하는 편이 좋습니다.",
    "신": "가까운 관계나 협업에서는 기준을 말로 먼저 설명하는 편이 좋습니다.",
    "유": "결과물을 다듬는 시간과 멈추는 시점을 같이 정하는 편이 좋습니다.",
    "술": "책임이 커 보이는 일일수록 상한선을 먼저 정해야 무리가 없습니다.",
    "해": "큰 결론은 오늘 하루를 다 보내고 난 뒤 다시 보는 편이 좋습니다.",
}


def calculate_daily_fortune(saju_result: dict, target_date: date) -> dict:
    """Return the fortune for a specific solar date."""
    day_pillar = get_day_pillar_for_solar_date(target_date)
    saju = saju_result["saju"]
    day_stem = saju["day"]["stem"]
    month_branch = saju["month"]["branch"]
    year_stem = saju["year"]["stem"]
    time_branch = saju["time"]["branch"] if saju.get("time") else None
    ten_god = calculate_ten_god_for_stem(day_stem, day_pillar["stem"])
    rule = DAILY_RULES[ten_god]
    natal_day_pillar_kor = saju["day"]["kor"]
    natal_day_pillar_line = DAY_PILLAR_SENTENCES[natal_day_pillar_kor]["daily"]

    sentence_data = load_analysis_sentences()
    ten_gods = calculate_ten_gods(saju)
    month_ten_god = ten_gods["ten_gods"]["month"]
    day_data = sentence_data["day_stem"][day_stem]
    month_data = sentence_data["month_branch"][month_branch]
    year_data = sentence_data["year_stem"][year_stem]
    time_data = sentence_data["time_branch"].get(time_branch) if time_branch else None
    month_ten_god_data = sentence_data["month_ten_god"].get(month_ten_god) if month_ten_god else None
    seed = target_date.toordinal()
    daily_profile = _resolve_daily_profile(day_stem, month_branch)
    headline = _build_daily_headline(
        profile=daily_profile,
        ten_god=ten_god,
        day_pillar_kor=day_pillar["kor"],
        natal_day_stem=day_stem,
        natal_month_branch=month_branch,
    )
    explanation = (
        f"{_strip_day_pillar_prefix(natal_day_pillar_line, natal_day_pillar_kor)} "
        f"{DAY_STEM_DAILY_LINES[day_stem]} "
        f"{rule['explanation']} "
        f"{DAILY_PROFILE_EXPLANATIONS[daily_profile]}"
    )
    advice = f"{rule['advice']} {DAILY_PROFILE_ADVICE[daily_profile]}"

    context_easy_lines = [
        natal_day_pillar_line,
        DAY_STEM_DAILY_LINES[day_stem],
        MONTH_BRANCH_DAILY_LINES[month_branch],
        _pick(day_data["social_reaction"], seed + 3),
        DAY_BRANCH_CONTEXT_LINES[day_pillar["branch"]],
    ]
    if month_ten_god_data:
        context_easy_lines.append(
            f"월간 십성 기준으로 보면 {_pick(month_ten_god_data['personality_modifier'], seed + 5).lower()}"
        )

    context_real_lines = [
        f"원국 일주 {natal_day_pillar_kor}{_object_particle(natal_day_pillar_kor)} 기준으로 보면 {_strip_day_pillar_prefix(natal_day_pillar_line, natal_day_pillar_kor)}",
        _pick(day_data["speech_style"], seed + 7),
        _pick(month_data["work_adaptation"], seed + 11),
        _pick(month_data["money_habit"], seed + 13),
        _pick(year_data["first_impression"], seed + 17),
    ]
    if time_data:
        context_real_lines.append(_pick(time_data["intimate_reaction"], seed + 19))

    context_action_lines = [
        f"오늘은 {format_stem_label(day_stem)} 일간 특유의 판단 순서를 지키되, 먼저 할 일 한두 가지만 눈에 보이게 정리하는 편이 좋습니다.",
        f"월지 {month_branch}의 생활 리듬을 기준으로 보면 {MONTH_BRANCH_DAILY_ACTIONS[month_branch]}",
        TIME_BRANCH_DAILY_ACTIONS[time_branch] if time_branch else f"오늘은 {rule['keywords'][0]}보다 {rule['keywords'][1]}를 먼저 정리하는 편이 좋습니다.",
    ]

    strength_lines = [
        DAILY_STRENGTH_LINES[ten_god],
        DAY_STEM_DAILY_STRENGTHS[day_stem],
        MONTH_BRANCH_DAILY_STRENGTHS[month_branch],
    ]
    risk_lines = [
        DAILY_RISK_LINES[ten_god],
        DAY_STEM_DAILY_RISKS[day_stem],
        MONTH_BRANCH_DAILY_RISKS[month_branch],
    ]
    if time_branch and time_data:
        risk_lines.append(_pick(time_data["intimate_reaction"], seed + 31))

    section = build_daily_section(
        headline=headline,
        explanation=explanation,
        advice=advice,
        keywords=rule["keywords"],
        seed=seed,
        context_easy_lines=context_easy_lines,
        context_real_lines=context_real_lines,
        context_action_lines=context_action_lines,
        strength_lines=strength_lines,
        risk_lines=risk_lines,
    )
    return {
        "date": target_date.isoformat(),
        "pillar": day_pillar["kor"],
        "hanja": day_pillar["hanja"],
        "stem": day_pillar["stem"],
        "branch": day_pillar["branch"],
        "ten_god": ten_god,
        "headline": section["one_line"],
        "summary": f"{natal_day_pillar_kor} 일주를 기준으로 보면 {DAY_STEM_HEADLINE_LINES[day_stem]} 오늘의 핵심은 {rule['keywords'][0]}과 {rule['keywords'][1]}입니다.",
        "explanation": " ".join(section["easy_explanation"]),
        "advice": " ".join(section["action_advice"]),
        "section": section,
        "keywords": rule["keywords"],
    }


def _pick(options: list[str], seed: int) -> str:
    return options[seed % len(options)]


def _resolve_daily_profile(day_stem: str, month_branch: str) -> str:
    if day_stem in {"갑", "을"} or month_branch in {"인", "묘"}:
        return "planner"
    if day_stem == "기" or month_branch in {"묘", "미"}:
        return "connector"
    if day_stem in {"병", "정"} or month_branch in {"사", "오"}:
        return "driver"
    if day_stem in {"무", "기"} or month_branch in {"축", "진", "미", "술"}:
        return "stabilizer"
    if day_stem in {"경", "신"} or month_branch in {"신", "유"}:
        return "precision"
    return "observer"


def _build_daily_headline(
    *,
    profile: str,
    ten_god: str,
    day_pillar_kor: str,
    natal_day_stem: str,
    natal_month_branch: str,
) -> str:
    focus = {
        "비견": "내 페이스를 지키는 방식",
        "겁재": "경쟁과 분산 관리",
        "식신": "실무 결과 만들기",
        "상관": "표현과 조율",
        "편재": "기회 선별",
        "정재": "생활 관리",
        "편관": "압박 대응",
        "정관": "책임과 신뢰",
        "편인": "관점 전환",
        "정인": "정리와 준비",
    }[ten_god]
    return (
        f"{day_pillar_kor} 일의 기운이 들어온 오늘은 "
        f"{DAY_STEM_HEADLINE_LINES[natal_day_stem]} "
        f"오늘의 핵심은 {focus}이고, "
        f"{MONTH_BRANCH_HEADLINE_LINES[natal_month_branch]}"
    )


def _strip_day_pillar_prefix(sentence: str, day_pillar_kor: str) -> str:
    prefixes = (
        f"{day_pillar_kor} 일주 기준으로 보면 ",
        f"{day_pillar_kor} 일주는 ",
    )
    for prefix in prefixes:
        if sentence.startswith(prefix):
            return sentence[len(prefix):].rstrip(".")
    return sentence.rstrip(".")


def _object_particle(word: str) -> str:
    if not word:
        return "를"
    last = ord(word[-1])
    if 0xAC00 <= last <= 0xD7A3:
        return "을" if (last - 0xAC00) % 28 else "를"
    return "를"
