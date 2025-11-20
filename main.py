import os
from datetime import datetime
from typing import Optional, Literal, List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import db, create_document
from bson import ObjectId

app = FastAPI(title="SaaS.ai - No-code Builder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Utilities ----------

def oid(obj_id: str) -> ObjectId:
    try:
        return ObjectId(obj_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")


def serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    # Convert datetimes to isoformat strings
    for k, v in list(doc.items()):
        if hasattr(v, "isoformat"):
            doc[k] = v.isoformat()
    return doc


# ---------- Schemas ----------

class IdeaIn(BaseModel):
    text: str = Field(..., description="Raw idea text from the user")


class ValidateOut(BaseModel):
    scores: Dict[str, int]
    risks: List[str]
    opportunities: List[str]
    recommendations: List[str]
    summary: str


class GenerateIn(BaseModel):
    idea_id: Optional[str] = None
    text: Optional[str] = None
    site_type: Literal["landing", "dashboard", "ecommerce", "blog"]
    notes: Optional[str] = None


class PrototypeOut(BaseModel):
    version_id: str
    idea_id: str
    version: int
    site_type: str
    code: str
    created_at: str


# ---------- Core logic ----------

KEYWORDS = {
    "education": ["teacher", "student", "lesson", "school", "course", "class"],
    "commerce": ["buy", "sell", "shop", "e-commerce", "payment", "checkout", "store"],
    "b2b": ["enterprise", "team", "workflow", "crm", "erp", "dashboard"],
    "content": ["blog", "post", "article", "newsletter", "content"],
    "ai": ["ai", "machine learning", "gpt", "model", "chatbot", "assistant"],
}


def score_idea(text: str) -> ValidateOut:
    t = text.lower()
    scores = {
        "market_feasibility": 5,
        "target_audience": 5,
        "monetization_potential": 5,
        "technical_complexity": 5,
    }

    # Heuristic boosts
    if any(k in t for k in KEYWORDS["ai"]):
        scores["market_feasibility"] += 2
        scores["monetization_potential"] += 1
        scores["technical_complexity"] += 2
    if any(k in t for k in KEYWORDS["b2b"]):
        scores["target_audience"] += 2
        scores["monetization_potential"] += 2
    if any(k in t for k in KEYWORDS["commerce"]):
        scores["monetization_potential"] += 3
    if any(k in t for k in KEYWORDS["education"]):
        scores["market_feasibility"] += 1
        scores["target_audience"] += 1
    if any(k in t for k in KEYWORDS["content"]):
        scores["market_feasibility"] += 1

    # Clamp 0..10
    for k in scores:
        scores[k] = max(0, min(10, scores[k]))

    risks = []
    if scores["technical_complexity"] >= 7:
        risks.append("High technical complexity may increase time-to-market and cost.")
    if "privacy" in t or "health" in t or "finance" in t:
        risks.append("Regulatory compliance (privacy/health/finance) may be required.")
    if "viral" in t or "social network" in t:
        risks.append("Network effects are hard to achieve without significant traction.")

    opportunities = []
    if any(k in t for k in KEYWORDS["ai"]):
        opportunities.append("Leverage AI differentiation for personalization and automation.")
    if any(k in t for k in KEYWORDS["b2b"]):
        opportunities.append("B2B sales with clear ROI can support premium pricing.")
    if any(k in t for k in KEYWORDS["commerce"]):
        opportunities.append("Direct monetization via subscriptions and transactions.")
    if any(k in t for k in KEYWORDS["education"]):
        opportunities.append("Large educator communities enable organic distribution.")

    recommendations = [
        "Start with a focused niche to validate demand quickly.",
        "Ship an MVP with 1-2 killer workflows before expanding scope.",
        "Define 1-2 monetization experiments (subscription tiers, usage-based).",
        "Add analytics to learn from early usage.",
    ]

    summary = (
        "Balanced opportunity with manageable risk. Start lean, validate with a prototype, "
        "and iterate based on user feedback."
    )

    return ValidateOut(
        scores=scores,
        risks=risks or ["Go-to-market and user acquisition remain key risks."],
        opportunities=opportunities or ["Opportunity to differentiate with excellent UX and speed."],
        recommendations=recommendations,
        summary=summary,
    )


def generate_code(site_type: str, idea_text: str) -> str:
    # Tailwind CDN single-file templates with simple components
    base_head = (
        "<meta charset='UTF-8'/>"
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'/>"
        "<script src='https://cdn.tailwindcss.com'></script>"
        "<title>SaaS.ai Prototype</title>"
    )
    # Simple color theme
    hero = f"""
    <header class='bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white'>
      <div class='max-w-6xl mx-auto px-6 py-20'>
        <h1 class='text-4xl md:text-6xl font-extrabold tracking-tight'>Prototype: {site_type.title()}</h1>
        <p class='mt-4 text-slate-300 text-lg'>Idea: {idea_text}</p>
        <div class='mt-8 flex gap-3'>
          <a href='#' class='px-5 py-3 rounded-lg bg-blue-600 hover:bg-blue-500 transition'>Get Started</a>
          <a href='#' class='px-5 py-3 rounded-lg bg-white/10 hover:bg-white/20 transition'>Learn More</a>
        </div>
      </div>
    </header>
    """

    sections = {
        "landing": """
        <section class='max-w-6xl mx-auto px-6 py-16 grid md:grid-cols-3 gap-8'>
          <div class='p-6 rounded-xl border border-slate-200/20 bg-white/5'>
            <h3 class='text-xl font-semibold text-white'>Problem</h3>
            <p class='mt-2 text-slate-300'>Describe the pain point your product solves.</p>
          </div>
          <div class='p-6 rounded-xl border border-slate-200/20 bg-white/5'>
            <h3 class='text-xl font-semibold text-white'>Solution</h3>
            <p class='mt-2 text-slate-300'>Show how you uniquely address the problem.</p>
          </div>
          <div class='p-6 rounded-xl border border-slate-200/20 bg-white/5'>
            <h3 class='text-xl font-semibold text-white'>Proof</h3>
            <p class='mt-2 text-slate-300'>Add testimonials, metrics, or social proof.</p>
          </div>
        </section>
        <section class='max-w-6xl mx-auto px-6 pb-20'>
          <div class='rounded-2xl border border-slate-200/20 bg-white/5 p-6'>
            <h3 class='text-xl font-semibold text-white'>Call to Action</h3>
            <div class='mt-4 flex gap-3'>
              <input placeholder='Email address' class='px-4 py-3 rounded-lg bg-white/10 text-white placeholder-slate-400 outline-none w-full md:w-72'>
              <button class='px-5 py-3 rounded-lg bg-blue-600 hover:bg-blue-500 transition'>Join Waitlist</button>
            </div>
          </div>
        </section>
        """,
        "dashboard": """
        <section class='max-w-6xl mx-auto px-6 py-16'>
          <div class='grid md:grid-cols-4 gap-6'>
            <div class='col-span-4 grid sm:grid-cols-4 gap-4'>
              <div class='p-4 rounded-xl bg-white/5 border border-slate-200/20'>
                <p class='text-slate-400 text-sm'>Active Users</p>
                <p class='text-2xl font-bold text-white'>1,284</p>
              </div>
              <div class='p-4 rounded-xl bg-white/5 border border-slate-200/20'>
                <p class='text-slate-400 text-sm'>MRR</p>
                <p class='text-2xl font-bold text-white'>$8,920</p>
              </div>
              <div class='p-4 rounded-xl bg-white/5 border border-slate-200/20'>
                <p class='text-slate-400 text-sm'>Churn</p>
                <p class='text-2xl font-bold text-white'>2.4%</p>
              </div>
              <div class='p-4 rounded-xl bg-white/5 border border-slate-200/20'>
                <p class='text-slate-400 text-sm'>Tickets</p>
                <p class='text-2xl font-bold text-white'>37</p>
              </div>
            </div>
            <div class='col-span-3 mt-6 rounded-xl bg-white/5 border border-slate-200/20 p-6'>
              <h3 class='text-white font-semibold'>Usage Over Time</h3>
              <div class='mt-4 h-48 rounded-lg bg-gradient-to-r from-blue-500/20 to-cyan-500/20'></div>
            </div>
            <div class='col-span-1 mt-6 rounded-xl bg-white/5 border border-slate-200/20 p-6'>
              <h3 class='text-white font-semibold'>Tasks</h3>
              <ul class='mt-2 space-y-2 text-slate-300'>
                <li>Follow up with leads</li>
                <li>Review signups</li>
                <li>Plan onboarding</li>
              </ul>
            </div>
          </div>
        </section>
        """,
        "ecommerce": """
        <section class='max-w-6xl mx-auto px-6 py-16'>
          <div class='grid sm:grid-cols-2 md:grid-cols-3 gap-6'>
            <div class='rounded-xl overflow-hidden bg-white/5 border border-slate-200/20'>
              <div class='h-40 bg-gradient-to-br from-blue-400 to-cyan-400'></div>
              <div class='p-4'>
                <p class='text-white font-semibold'>Starter Plan</p>
                <p class='text-slate-300'>$19</p>
                <button class='mt-3 w-full px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500'>Add to Cart</button>
              </div>
            </div>
            <div class='rounded-xl overflow-hidden bg-white/5 border border-slate-200/20'>
              <div class='h-40 bg-gradient-to-br from-purple-400 to-pink-400'></div>
              <div class='p-4'>
                <p class='text-white font-semibold'>Pro Plan</p>
                <p class='text-slate-300'>$49</p>
                <button class='mt-3 w-full px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500'>Add to Cart</button>
              </div>
            </div>
            <div class='rounded-xl overflow-hidden bg-white/5 border border-slate-200/20'>
              <div class='h-40 bg-gradient-to-br from-emerald-400 to-teal-400'></div>
              <div class='p-4'>
                <p class='text-white font-semibold'>Enterprise</p>
                <p class='text-slate-300'>$199</p>
                <button class='mt-3 w-full px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500'>Contact Sales</button>
              </div>
            </div>
          </div>
        </section>
        """,
        "blog": """
        <section class='max-w-3xl mx-auto px-6 py-16'>
          <article class='prose prose-invert'>
            <h2>Introducing Our New Prototype</h2>
            <p>This is a minimal blog layout generated for your idea. Replace this text with your own content and publish.</p>
            <h3>Why it matters</h3>
            <ul>
              <li>Fast to iterate</li>
              <li>Simple to customize</li>
              <li>Clean, modern design</li>
            </ul>
          </article>
          <div class='mt-10 grid gap-6 sm:grid-cols-2'>
            <a class='p-4 rounded-xl bg-white/5 border border-slate-200/20 block'>How we validate product ideas</a>
            <a class='p-4 rounded-xl bg-white/5 border border-slate-200/20 block'>Designing dashboards that delight</a>
          </div>
        </section>
        """,
    }

    body = f"""
    <!doctype html>
    <html>
      <head>{base_head}</head>
      <body class='min-h-screen bg-slate-950'>
        {hero}
        {sections.get(site_type, sections['landing'])}
        <footer class='py-10 text-center text-slate-400'>Built with SaaS.ai</footer>
      </body>
    </html>
    """
    return body


# ---------- Routes ----------

@app.get("/")
def root():
    return {"message": "SaaS.ai API is running"}


@app.post("/api/ideas")
def create_idea(idea: IdeaIn):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    doc = {
        "text": idea.text,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    inserted_id = db["idea"].insert_one(doc).inserted_id
    return {"idea_id": str(inserted_id)}


@app.get("/api/ideas/{idea_id}")
def get_idea(idea_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    doc = db["idea"].find_one({"_id": oid(idea_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Idea not found")
    return serialize(doc)


@app.get("/api/ideas/{idea_id}/versions")
def list_versions(idea_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    cur = db["prototypeversion"].find({"idea_id": idea_id}).sort("version", -1)
    items = [serialize(d) for d in cur]
    return {"count": len(items), "items": items}


@app.get("/api/versions/{version_id}")
def get_version(version_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    doc = db["prototypeversion"].find_one({"_id": oid(version_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Version not found")
    return serialize(doc)


@app.post("/api/validate", response_model=ValidateOut)
def validate_idea(idea: IdeaIn):
    return score_idea(idea.text)


@app.post("/api/generate", response_model=PrototypeOut)
def generate_prototype(payload: GenerateIn):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    # Ensure idea exists or create from text
    idea_id = payload.idea_id
    if not idea_id:
        if not payload.text:
            raise HTTPException(status_code=400, detail="Provide idea_id or text")
        idea_id = str(db["idea"].insert_one({
            "text": payload.text,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }).inserted_id)
        idea_text = payload.text
    else:
        idea_doc = db["idea"].find_one({"_id": oid(idea_id)})
        if not idea_doc:
            raise HTTPException(status_code=404, detail="Idea not found")
        idea_text = idea_doc.get("text", payload.text or "")

    # Determine next version
    last = db["prototypeversion"].find({"idea_id": idea_id}).sort("version", -1).limit(1)
    next_version = 1
    for d in last:
        next_version = int(d.get("version", 0)) + 1

    code = generate_code(payload.site_type, idea_text)

    doc = {
        "idea_id": idea_id,
        "idea_text": idea_text,
        "site_type": payload.site_type,
        "version": next_version,
        "code": code,
        "notes": payload.notes,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    inserted_id = db["prototypeversion"].insert_one(doc).inserted_id
    saved = db["prototypeversion"].find_one({"_id": inserted_id})

    s = serialize(saved)
    return PrototypeOut(
        version_id=s["id"],
        idea_id=s["idea_id"],
        version=s["version"],
        site_type=s["site_type"],
        code=s["code"],
        created_at=s.get("created_at", ""),
    )


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
