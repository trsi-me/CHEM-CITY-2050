import re
from datetime import datetime, timedelta, timezone

START = {"water": 30, "air": 26, "energy": 20, "budget": 1150}
ORDER = ["water", "air", "energy"]

STAGES = {
    "water": {
        "step": 1,
        "name": "المياه",
        "title": "أزمة المياه",
        "lead": "مؤشر جودة المياه يجمع العكارة والمعادن والميكروبات. الخطر الأكبر الآن رصاص مذاب في ماء حمضي.",
        "facts": [
            {"label": "العكارة", "value": "90 NTU"},
            {"label": "الرصاص", "value": "Pb2+ فوق الحد"},
            {"label": "الأس الهيدروجيني", "value": "5.6"},
            {"label": "الميكروبات", "value": "ارتفاع محدود"},
        ],
        "question": "أي معالجة تُخرج أيونات الرصاص المذابة من الماء؟",
        "options": [
            {"id": "sand", "text": "الترشيح الرملي وحده"},
            {"id": "precip", "text": "رفع الأس الهيدروجيني بالجير حتى يترسب Pb(OH)2"},
            {"id": "settle", "text": "تركيد الجسيمات بالجاذبية"},
        ],
        "answer": "precip",
        "quiz_concept": "إخراج الأيون المذاب بالترسيب لا بالترشيح",
        "quiz_ok": "الإجابة تطابق سلوك المادة في هذه الأزمة.",
        "quiz_bad": "الرصاص هنا مذاب. الرمل والجاذبية يحجزان العالق، والجير يرسبه على هيئة Pb(OH)2.",
        "choices": [
            {
                "id": "alum",
                "title": "تخثير بالشب ثم ترشيح",
                "text": "الشب يجمع الطين الغروي، ثم يرسب المرشح الندف.",
                "cost": 260,
                "water": 22,
                "air": 0,
                "energy": -4,
                "concept": "التخثير بالشب للعكارة",
                "equation": "Al2(SO4)3 + 6H2O -> 2Al(OH)3 + 3H2SO4",
                "explanation": "الشب يكوّن هيدروكسيد الألومنيوم الذي يجمع الجسيمات الغروية فتنخفض العكارة، والحمض في المعادلة المبسطة تستهلكه قلوية الماء. معظم أيونات الرصاص تبقى مذابة لأن المرشح الرملي لا يحجزها.",
            },
            {
                "id": "lime",
                "title": "ترسيب بالجير ثم ترشيح",
                "text": "الجير يرفع الأس الهيدروجيني فيترسب الرصاص، ثم يحجزه الترشيح.",
                "cost": 400,
                "water": 40,
                "air": 0,
                "energy": -4,
                "concept": "الترسيب الكيميائي للمعادن المذابة",
                "equation": "Pb2+ + 2OH- -> Pb(OH)2",
                "explanation": "هيدروكسيد الكالسيوم يرفع الأس الهيدروجيني ضمن المدى الذي يرسب فيه الرصاص، والترشيح يحجز Pb(OH)2. هذه المعالجة تناسب المعدن المذاب في الماء الحمضي.",
            },
            {
                "id": "chlorine",
                "title": "كلورة فقط",
                "text": "الكلور يكوّن حمضًا يقتل الميكروبات ولا يمس المعدن المذاب.",
                "cost": 150,
                "water": 6,
                "air": 0,
                "energy": -2,
                "concept": "حدود التطهير بالكلور",
                "equation": "Cl2 + H2O -> HOCl + HCl",
                "explanation": "حمض الهيبوكلوروز يقتل الميكروبات. لا يزيل العكارة ولا أيونات الرصاص، فمؤشر المياه يتحرك قليلًا.",
            },
        ],
    },
    "air": {
        "step": 2,
        "name": "الهواء",
        "title": "أزمة الهواء",
        "lead": "مؤشر الهواء يتبع ثاني أكسيد الكبريت والجسيمات وأكاسيد النيتروجين. القراءة الحالية يقودها SO2.",
        "facts": [
            {"label": "ثاني أكسيد الكبريت", "value": "3 أضعاف الحد"},
            {"label": "الجسيمات", "value": "PM2.5 متوسط"},
            {"label": "أكاسيد النيتروجين", "value": "قرب الحد"},
            {"label": "المصدر", "value": "وقود كبريتي"},
        ],
        "question": "في غسل غاز المداخن، ماذا يُفصل عن الدخان بعد التقاء SO2 مع Ca(OH)2؟",
        "options": [
            {"id": "salt", "text": "ملح صلب من كبريتيت الكالسيوم أو كبريتاته"},
            {"id": "stay", "text": "يبقى SO2 كما هو داخل البرج"},
            {"id": "carbon", "text": "أول أكسيد الكربون"},
        ],
        "answer": "salt",
        "quiz_concept": "تحويل SO2 إلى ملح كالسيوم صلب",
        "quiz_ok": "الإجابة تطابق سلوك المادة في هذه الأزمة.",
        "quiz_bad": "الجير يحول SO2 إلى ملح كالسيوم صلب يُفصل عن الدخان، ولا ينتج أول أكسيد الكربون.",
        "choices": [
            {
                "id": "fgd",
                "title": "غسل المداخن بالجير",
                "text": "برج غسل يلاقي دخان الكبريت برذاذ الجير.",
                "cost": 380,
                "water": -6,
                "air": 34,
                "energy": -8,
                "concept": "إزالة الكبريت من غاز المداخن",
                "equation": "SO2 + Ca(OH)2 -> CaSO3 + H2O",
                "explanation": "SO2 غاز حمضي يتحول مع الجير إلى ملح صلب يُفصل عن الدخان، ثم يتأكسد غالبًا إلى جبس. مضخات البرج تستهلك كهرباء، وماء الغسل ينقل جزءًا من التلوث إلى مسار المياه.",
            },
            {
                "id": "scr",
                "title": "اختزال حفزي لأكاسيد النيتروجين",
                "text": "حفاز وأمونيا لاختزال أكاسيد النيتروجين.",
                "cost": 420,
                "water": 0,
                "air": 12,
                "energy": -6,
                "concept": "الاختزال الحفزي الانتقائي",
                "equation": "4NO + 4NH3 + O2 -> 4N2 + 6H2O",
                "explanation": "الأمونيا تختزل أكاسيد النيتروجين على الحفاز إلى نيتروجين وماء. أزمة المدينة يقودها SO2، لذلك التحسن في الهواء محدود.",
            },
            {
                "id": "source",
                "title": "تقليل الكبريت من المصدر",
                "text": "وقود أقل كبريتًا مع ضبط الاحتراق من المصدر.",
                "cost": 250,
                "water": 0,
                "air": 26,
                "energy": 8,
                "concept": "منع تكوّن SO2 عند الاحتراق",
                "equation": "S + O2 -> SO2",
                "explanation": "كبريت الوقود يحترق إلى SO2. خفض الكبريت يقلل الغاز من مصدره، وضبط الاحتراق يرفع كفاءة الطاقة. الأثر أهدأ من برج الغسل في ذروة التلوث، وأوفر في الميزانية.",
            },
        ],
    },
    "energy": {
        "step": 3,
        "name": "الطاقة",
        "title": "أزمة الطاقة",
        "lead": "مؤشر الطاقة يتبع التوليد بلا احتراق وقدرة المدينة على تغطية الليل. النهار مشمس، والفائض يُهدر.",
        "facts": [
            {"label": "النهار", "value": "فائض يُهدر"},
            {"label": "الليل", "value": "عجز متكرر"},
            {"label": "الشبكة الآن", "value": "احتراق"},
            {"label": "المناخ", "value": "تشميس عالٍ"},
        ],
        "question": "عند تفريغ بطارية أيون الليثيوم، أين تذهب أيونات الليثيوم؟",
        "options": [
            {"id": "wire", "text": "عبر السلك الخارجي مع الإلكترونات"},
            {"id": "ions", "text": "من الجرافيت عبر الإلكتروليت إلى المهبط"},
            {"id": "gas", "text": "تتصاعد غاز ليثيوم في التشغيل السليم"},
        ],
        "answer": "ions",
        "quiz_concept": "حركة أيون الليثيوم أثناء التفريغ",
        "quiz_ok": "الإجابة تطابق سلوك المادة في هذه الأزمة.",
        "quiz_bad": "الإلكترونات تسري في السلك، وأيونات الليثيوم تعبر الإلكتروليت من الجرافيت إلى المهبط.",
        "choices": [
            {
                "id": "solar",
                "title": "توسعة الخلايا الشمسية",
                "text": "خلايا سيليكون تولد تيارًا من الضوء بلا احتراق.",
                "cost": 480,
                "water": 0,
                "air": 10,
                "energy": 36,
                "concept": "الأثر الكهروضوئي في السيليكون",
                "equation": "",
                "explanation": "الفوتون يحرر إلكترونًا في خلية السيليكون فينشأ تيار بلا احتراق، فينخفض ما تطلقه المحطات من SO2. الإنتاج نهاري، وبعد الغروب تعود الشبكة إلى التخزين أو الوقود.",
            },
            {
                "id": "battery",
                "title": "بطاريات أيون الليثيوم",
                "text": "تخزين الفائض النهاري لاستخدامه ليلًا.",
                "cost": 340,
                "water": 0,
                "air": 4,
                "energy": 26,
                "concept": "تخزين الطاقة بتفاعل أيون الليثيوم",
                "equation": "LiC6 -> Li+ + e- + C6",
                "explanation": "عند التفريغ تخرج أيونات الليثيوم من بين طبقات الجرافيت وتعبر الإلكتروليت إلى المهبط، بينما الإلكترونات تسري في الدائرة. البطارية لا تصنع طاقة، بل تحفظ الفائض لليل.",
            },
            {
                "id": "fossil",
                "title": "زيادة حرق الوقود",
                "text": "سد العجز فورًا بمزيد من الاحتراق.",
                "cost": 170,
                "water": 0,
                "air": -16,
                "energy": 14,
                "concept": "نواتج احتراق الوقود الكبريتي",
                "equation": "S + O2 -> SO2",
                "explanation": "الاحتراق يسد العجز بسرعة. كبريت الوقود يتأكسد إلى SO2 فيعود التلوث إلى الهواء، وتتراجع استدامة المدينة.",
            },
        ],
    },
}

def clamp(value):
    return max(0, min(100, int(value)))

def new_state():
    return {
        "water": START["water"],
        "air": START["air"],
        "energy": START["energy"],
        "budget": START["budget"],
    }

def sustainability(water, air, energy):
    raw = (0.34 * water) + (0.33 * air) + (0.33 * energy)
    return clamp(int(raw + 0.5))

def clean_leader(raw):
    name = " ".join(str(raw or "").split())
    if len(name) < 2 or len(name) > 40:
        return ""
    if "<" in name or ">" in name:
        return ""
    if re.fullmatch(r"[\w .\-]{2,40}", name, flags=re.UNICODE) is None:
        return ""
    return name

def format_ksa(value):
    moment = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    moment = moment + timedelta(hours=3)
    hour = moment.hour
    suffix = "ص" if hour < 12 else "م"
    hour12 = hour % 12
    if hour12 == 0:
        hour12 = 12
    return f"{moment.year}/{moment.month}/{moment.day}م {hour12}:{moment.minute:02d}{suffix}"

def apply(state, stage_id, choice_id, quiz_id):
    stage = STAGES.get(stage_id)
    if stage is None:
        return state, None, "choice"
    choice = None
    for item in stage["choices"]:
        if item["id"] == choice_id:
            choice = item
            break
    if choice is None:
        return state, None, "choice"
    known = [item["id"] for item in stage["options"]]
    if quiz_id not in known:
        return state, None, "quiz"
    if choice["cost"] > state["budget"]:
        return state, None, "budget"
    nxt = {
        "water": clamp(state["water"] + choice["water"]),
        "air": clamp(state["air"] + choice["air"]),
        "energy": clamp(state["energy"] + choice["energy"]),
        "budget": state["budget"] - choice["cost"],
    }
    decision = {
        "choice_id": choice["id"],
        "choice_title": choice["title"],
        "cost": choice["cost"],
        "quiz_ok": 1 if quiz_id == stage["answer"] else 0,
        "concept": choice["concept"],
        "quiz_concept": stage["quiz_concept"],
        "equation": choice["equation"],
        "explanation": choice["explanation"],
        "quiz_note": stage["quiz_ok"] if quiz_id == stage["answer"] else stage["quiz_bad"],
    }
    return nxt, decision, None

def verdict(state):
    score = sustainability(state["water"], state["air"], state["energy"])
    low = min(state["water"], state["air"], state["energy"])
    if low >= 50 and score >= 55:
        return "saved", "الخطة أنقذت المدينة", "المؤشرات الثلاثة فوق حد الخطر، والميزانية نفّذت الخطة.", score
    if score >= 45:
        return "partial", "المدينة استقرت جزئيًا", "بعض المؤشرات تحسنت، وما زال مورد دون حد الأمان.", score
    return "collapse", "المدينة لم تُنقذ", "المؤشرات بقيت تحت حد الخطر.", score

def pulse(state):
    def band(value, low, mid, high):
        if value < 50:
            return low
        if value < 70:
            return mid
        return high

    parts = [
        band(state["water"], "المياه تحت حد الخطر", "المياه تتحسن", "المياه في مستوى مقبول"),
        band(state["air"], "الهواء ما زال ثقيلًا", "الهواء بدأ يصفو", "الهواء في مستوى مقبول"),
        band(state["energy"], "الطاقة لا تغطي الليل", "الطاقة تقترب من الكفاية", "الطاقة تغطي الطلب"),
    ]
    return "، ".join(parts)

def public_stage(stage_id, budget):
    stage = STAGES[stage_id]
    choices = []
    for item in stage["choices"]:
        choices.append({
            "id": item["id"],
            "title": item["title"],
            "text": item["text"],
            "cost": item["cost"],
            "ok": item["cost"] <= budget,
        })
    return {
        "id": stage_id,
        "title": stage["title"],
        "lead": stage["lead"],
        "facts": stage["facts"],
        "question": stage["question"],
        "options": stage["options"],
        "choices": choices,
    }

def concepts_of(decisions):
    got = []
    missed = []
    for item in decisions:
        if item["quiz_ok"]:
            if item["quiz_concept"] not in got:
                got.append(item["quiz_concept"])
        elif item["quiz_concept"] not in missed:
            missed.append(item["quiz_concept"])
        if item["concept"] not in got:
            got.append(item["concept"])
    return got, missed

def recommendations(state):
    items = []
    if state["water"] < 70:
        items.append("أكملي إخراج الرصاص بالجير قبل إعادة استخدام الخزان للصناعة.")
    if state["air"] < 70:
        items.append("ثبّتي وقودًا منخفض الكبريت، وأضيفي غسل المداخن إذا بقي SO2 مرتفعًا.")
    if state["energy"] < 70:
        items.append("اجمعي التوليد الشمسي مع بطارية أيون الليثيوم حتى لا يعود الليل إلى الاحتراق.")
    if state["budget"] < 80:
        items.append("الرصيد ضيق، فأي توسعة لاحقة تبدأ بخفض الهدر.")
    if not items:
        items.append("حافظي على إزالة المعدن المذاب، ووقود منخفض الكبريت، وتخزين يكفي بعد الغروب.")
    return items[:3]

def _path(state, steps):
    current = dict(state)
    rows = []
    for stage_id, choice_id, quiz_id in steps:
        current, decision, err = apply(current, stage_id, choice_id, quiz_id)
        if err:
            return current, rows, err
        rows.append(decision)
    return current, rows, None

def self_check():
    assert clean_leader("  قائدة المدينة  ") == "قائدة المدينة"
    assert clean_leader("أ") == ""
    assert clean_leader("<b>") == ""
    assert format_ksa("2026-01-03T02:50:00Z") == "2026/1/3م 5:50ص"
    assert format_ksa("2026-01-03T21:00:00Z") == "2026/1/4م 12:00ص"
    won, _, err = _path(new_state(), [("water", "lime", "precip"), ("air", "source", "salt"), ("energy", "solar", "ions")])
    assert err is None
    assert won == {"water": 70, "air": 62, "energy": 60, "budget": 20}
    assert verdict(won)[0] == "saved"
    assert verdict(won)[3] == 64
    partial, _, err = _path(new_state(), [("water", "lime", "precip"), ("air", "fgd", "salt"), ("energy", "battery", "ions")])
    assert err is None
    assert partial["energy"] == 34
    assert verdict(partial)[0] == "partial"
    lost, rows, err = _path(new_state(), [("water", "chlorine", "sand"), ("air", "scr", "stay"), ("energy", "fossil", "wire")])
    assert err is None
    assert rows[0]["quiz_ok"] == 0
    assert verdict(lost)[0] == "collapse"
    same, _, err = apply({"water": 30, "air": 26, "energy": 20, "budget": 100}, "water", "lime", "precip")
    assert err == "budget"
    assert same["budget"] == 100
    blocked, _, err = apply(new_state(), "water", "solar", "precip")
    assert err == "choice"
    assert blocked["budget"] == 1150
    high, decision, err = apply({"water": 90, "air": 10, "energy": 10, "budget": 5000}, "water", "lime", "sand")
    assert err is None
    assert high["water"] == 100
    assert decision["quiz_ok"] == 0
    got, missed = concepts_of([{"quiz_ok": 1, "quiz_concept": "أ", "concept": "ب"}, {"quiz_ok": 0, "quiz_concept": "ج", "concept": "د"}])
    assert got == ["أ", "ب", "د"]
    assert missed == ["ج"]
    assert len(recommendations(won)) <= 3
    hidden = public_stage("water", 100)
    assert "answer" not in hidden
    assert "water" not in hidden["choices"][0]
    assert hidden["choices"][0]["ok"] is False
    assert public_stage("water", 1150)["choices"][0]["ok"] is True
    print("ok")

if __name__ == "__main__":
    self_check()
