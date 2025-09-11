import json, re
from pathlib import Path
from rapidfuzz import fuzz
import streamlit as st

KB_PATH = Path(__file__).with_name("kb.json")

def normalize(t: str) -> str:
    if not t:
        return ""
    t = t.lower()
    # simplifier les mots arabes
    t = re.sub(r'[\u0617-\u061A\u064B-\u0652\u0670\u06D6-\u06ED\u0640]', '', t)
    # simplifier les mots français
    repl = str.maketrans("éèêàâîïôûùç", "eeeaaio uuc")
    t = t.translate(repl)
    # éléminer les symboles
    t = re.sub(r'[^a-z\u0600-\u06FF0-9\s]', ' ', t)
    # éviter les espaces
    t = re.sub(r'\s+', ' ', t).strip()
    return t

@st.cache_data
def load_kb():
    data = json.loads(KB_PATH.read_text(encoding="utf-8"))
    # faire normalize
    for c in data["conditions"]:
        c["core_norm"]  = [normalize(p) for p in c.get("core", [])]
        c["other_norm"] = [normalize(p) for p in c.get("other", [])]
        c["red_norm"]   = [normalize(p) for p in c.get("red_flags", [])]
    data["global_red_norm"] = [normalize(p) for p in data.get("global_red_flags", [])]
    return data

def any_red_flags(user_txt, kb):
    txt = normalize(user_txt)
    for p in kb["global_red_norm"]:
        if fuzz.partial_ratio(p, txt) >= 85:
            return True, p
    for c in kb["conditions"]:
        for p in c["red_norm"]:
            if fuzz.partial_ratio(p, txt) >= 85:
                return True, p
    return False, None

def score_condition(user_txt, cond):
    txt = normalize(user_txt)
    score = 0
    hits = []
    for p in cond["core_norm"]:
        if fuzz.partial_ratio(p, txt) >= 82:
            score += 2
            hits.append(p)
    for p in cond["other_norm"]:
        if fuzz.partial_ratio(p, txt) >= 82:
            score += 1
            hits.append(p)
    return score, hits

#créer une interface de site web
def main():
    st.set_page_config(page_title="Docteur Virtuel (Triage)", page_icon="🩺")
    st.title("🩺 Docteur Virtuel — Triage تعليمي")
    st.caption("⚠️ غير موجّه للتشخيص النهائي. لأي حالة خطيرة أو شك، تواصل مع طبيب/الإسعاف فورًا.")

    kb = load_kb()

    st.subheader("دخل الأعراض ديالك (دارجة/عربية/فرنسية)")
    default_hint = "مثال: سخانة وكحة وحلاقم من البارح... / fièvre + toux + mal de gorge depuis hier"
    user_txt = st.text_area("أعراضك:", value="", placeholder=default_hint, height=120)

    if st.button("شوف الاحتمالات"):
        if not user_txt.strip():
            st.warning("كتب شي أعراض باش نقدر نحلّل.")
            return

        # red flags
        red, phrase = any_red_flags(user_txt, kb)
        if red:
            st.error("🔴 كاين عرض خطير! من الأفضل تتواصل مع الإسعاف/طبيب حالًا.")
            st.write(f"عبارة مطابقة تم رصدها: **{phrase}**")

        # calculer le score pour vérifier les symptomes
        scored = []
        for c in kb["conditions"]:
            s, hits = score_condition(user_txt, c)
            if s > 0:
                scored.append({"id": c["id"], "name": c["name"], "score": s, "hits": hits, "advice": c["advice"]})

        if not scored:
            st.info("ما لقيتش تطابق واضح. حاول توضّح الأعراض (المدة، الشدة، واش كاين حمى...).")
            return

        # Trier et afficher les résultats
        scored.sort(key=lambda x: x["score"], reverse=True)
        total = sum(x["score"] for x in scored) or 1
        st.subheader("👩‍⚕️ أقرب الاحتمالات (تقدير أولي)")
        for i, x in enumerate(scored[:3], start=1):
            pct = round((x["score"] / total) * 100)
            st.write(f"**{i}. {x['name']}** — تقدير: ~{pct}%")
            if x["hits"]:
                st.caption("تطابق مع: " + ", ".join(x["hits"]))
            with st.expander("نصيحة أولية"):
                st.write(x["advice"])

        st.divider()
        st.write("🔎 *نصيحة عامة:* راقب الأعراض خلال 48–72 ساعة. إذا ساءت الحالة أو ظهرت أعلام حمراء، تواصل فورًا مع طبيب/الإسعاف.")

if __name__ == "__main__":
    main()

