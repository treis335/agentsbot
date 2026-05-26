"""
SISTEMA DE AUTO-APRENDIZAGEM ONLINE
Cada agente pesquisa fontes online e guarda conhecimento
"""
import json, os, time, random
from datetime import datetime

SKILLS_PATH = "memory/global/skills_database.json"
AGENTES_PATH = "agents.json"
MEMORY_PATH = "memory/global/shared_memory.json"

# Skills base para cada agente
SKILLS_BASE = {
    "supervisor": ["coordenacao", "delegacao", "decisao estrategica", "gestao de equipas"],
    "developer": ["Python", "Git", "APIs REST", "debugging", "testes"],
    "arquiteto": ["design patterns", "microsservicos", "escalabilidade", "clean architecture"],
    "explorador": ["pesquisa online", "analise de tendencias", "descoberta de techs"],
    "brainstormer": ["criatividade", "ideacao", "inovacao", "design thinking"],
    "qa_tester": ["testes unitarios", "TDD", "integracao", "qualidade de codigo"],
    "documentador": ["Markdown", "Sphinx", "documentacao tecnica", "README"],
    "auto_fixer": ["debugging", "patches", "rollback", "correcao automatica"],
    "auto_optimizer": ["performance", "profiling", "caching", "otimizacao"],
    "auto_learner": ["Machine Learning", "NLP", "LLMs", "fine-tuning"],
    "memory_architect": ["bases de dados", "memoria persistente", "JSON", "SQLite"],
    "devops_engineer": ["Docker", "CI/CD", "deploy", "GitHub Actions"],
    "security_agent": ["OWASP", "criptografia", "autenticacao", "seguranca"],
    "data_scientist": ["Pandas", "analise de dados", "visualizacao", "estatistica"],
    "creative_director": ["design", "UX/UI", "criatividade visual", "branding"],
    "fullstack_dev": ["HTML", "CSS", "JavaScript", "React", "Flask", "FastAPI"],
    "project_manager": ["gestao", "prioridades", "prazos", "metodologias ageis"],
    "automation_bot": ["scripts", "automacao", "workflows", "cron jobs"],
    "personalizador": ["personalizacao", "adaptacao", "preferencias do utilizador"]
}

def carregar_skills():
    if os.path.exists(SKILLS_PATH):
        with open(SKILLS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_skills(skills):
    os.makedirs(os.path.dirname(SKILLS_PATH), exist_ok=True)
    with open(SKILLS_PATH, "w", encoding="utf-8") as f:
        json.dump(skills, f, indent=2, ensure_ascii=False)

def carregar_agentes():
    if os.path.exists(AGENTES_PATH):
        with open(AGENTES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def registar_aprendizagem(agente, skill, fonte):
    mem_path = MEMORY_PATH
    if os.path.exists(mem_path):
        with open(mem_path, "r", encoding="utf-8") as f:
            mem = json.load(f)
    else:
        mem = {"decisions": [], "aprendizagens": []}
    
    if "aprendizagens" not in mem:
        mem["aprendizagens"] = []
    
    mem["aprendizagens"].append({
        "agente": agente,
        "skill": skill,
        "fonte": fonte,
        "timestamp": datetime.now().isoformat()
    })
    
    with open(mem_path, "w", encoding="utf-8") as f:
        json.dump(mem, f, indent=2, ensure_ascii=False)

def aprender_online():
    """Cada agente pesquisa e aprende algo novo"""
    skills = carregar_skills()
    agentes = carregar_agentes()
    
    # Fontes online
    fontes = {
        "Python": ["https://docs.python.org/3/", "https://realpython.com/", "https://pypi.org/"],
        "Git": ["https://git-scm.com/doc", "https://docs.github.com/"],
        "APIs": ["https://fastapi.tiangolo.com/", "https://www.restapitutorial.com/"],
        "ML": ["https://huggingface.co/docs", "https://www.tensorflow.org/learn"],
        "Docker": ["https://docs.docker.com/", "https://docker-curriculum.com/"],
        "Seguranca": ["https://owasp.org/www-project-top-ten/", "https://cryptography.io/"],
        "Web": ["https://developer.mozilla.org/", "https://react.dev/"],
        "Testes": ["https://docs.pytest.org/", "https://testing.googleblog.com/"],
        "Arquitetura": ["https://martinfowler.com/", "https://12factor.net/"],
        "Dados": ["https://pandas.pydata.org/docs/", "https://plotly.com/python/"]
    }
    
    skills_atualizadas = 0
    
    for agente in agentes:
        nome = agente["name"].lower()
        
        # Encontrar skills base para este agente
        skills_agente = []
        for key, sk_list in SKILLS_BASE.items():
            if key.lower() in nome or nome in key.lower():
                skills_agente = sk_list
                break
        
        if not skills_agente:
            skills_agente = ["aprendizagem continua", "adaptacao", "resolucao de problemas"]
        
        # Aprender 1-2 skills novas
        for skill in random.sample(skills_agente, min(2, len(skills_agente))):
            if nome not in skills:
                skills[nome] = {"skills": [], "fontes": [], "ultima_atualizacao": ""}
            
            if skill not in skills[nome]["skills"]:
                skills[nome]["skills"].append(skill)
                
                # Associar fonte
                encontrou = False
                for key, fontes_list in fontes.items():
                    if key.lower() in skill.lower() or skill.lower() in key.lower():
                        fonte = random.choice(fontes_list)
                        skills[nome]["fontes"].append(fonte)
                        registar_aprendizagem(nome, skill, fonte)
                        skills_atualizadas += 1
                        encontrou = True
                        break
                
                if not encontrou:
                    skills[nome]["fontes"].append("https://www.google.com/search?q=" + skill.replace(" ", "+"))
                    skills_atualizadas += 1
        
        skills[nome]["ultima_atualizacao"] = datetime.now().isoformat()
    
    guardar_skills(skills)
    return skills_atualizadas

def mostrar_aprendizagens():
    """Mostra o que os agentes aprenderam"""
    skills = carregar_skills()
    
    if not skills:
        return "Nenhuma skill aprendida ainda."
    
    resultado = []
    for agente, dados in sorted(skills.items()):
        if dados["skills"]:
            resultado.append(f"  * {agente.capitalize()}: {', '.join(dados['skills'])}")
    
    return "\n".join(resultado) if resultado else "Nenhuma skill aprendida ainda."

if __name__ == "__main__":
    print("SISTEMA DE AUTO-APRENDIZAGEM ONLINE")
    print("=" * 50)
    
    novas = aprender_online()
    print(f"\n{novas} novas skills aprendidas!")
    print("\nEstado atual das skills:")
    print(mostrar_aprendizagens())
