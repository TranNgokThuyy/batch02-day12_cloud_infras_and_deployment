"""Production readiness checker for the Day 12 final project."""
import os
import sys


def check(name: str, passed: bool, detail: str = "") -> dict:
    icon = "[OK]" if passed else "[FAIL]"
    suffix = f" - {detail}" if detail else ""
    print(f"  {icon} {name}{suffix}")
    return {"name": name, "passed": passed}


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as file:
        return file.read()


def run_checks() -> bool:
    results = []
    base = os.path.dirname(__file__)

    print()
    print("=" * 55)
    print("  Production Readiness Check - Day 12 Lab")
    print("=" * 55)

    print("\nRequired Files")
    for filename in [
        "Dockerfile",
        "docker-compose.yml",
        ".dockerignore",
        ".env.example",
        "requirements.txt",
        "utils/mock_llm.py",
        "MISSION_ANSWERS.md",
        "DEPLOYMENT.md",
    ]:
        results.append(check(f"{filename} exists", os.path.exists(os.path.join(base, filename))))

    results.append(
        check(
            "railway.toml or render.yaml exists",
            os.path.exists(os.path.join(base, "railway.toml"))
            or os.path.exists(os.path.join(base, "render.yaml")),
        )
    )

    print("\nRequired App Modules")
    for filename in [
        "app/main.py",
        "app/config.py",
        "app/auth.py",
        "app/rate_limiter.py",
        "app/cost_guard.py",
    ]:
        results.append(check(f"{filename} exists", os.path.exists(os.path.join(base, filename))))

    print("\nSecurity")
    env_ignored = False
    for gitignore in [os.path.join(base, ".gitignore"), os.path.join(base, "..", ".gitignore")]:
        if os.path.exists(gitignore) and ".env" in read_text(gitignore):
            env_ignored = True
            break
    results.append(check(".env is ignored", env_ignored, "Add .env to .gitignore" if not env_ignored else ""))

    secrets_found = []
    for filename in ["app/main.py", "app/config.py", "app/auth.py"]:
        path = os.path.join(base, filename)
        if os.path.exists(path):
            content = read_text(path)
            for marker in ["sk-", "password123"]:
                if marker in content:
                    secrets_found.append(f"{filename}:{marker}")
    results.append(check("No obvious hardcoded secrets", not secrets_found, ", ".join(secrets_found)))

    print("\nAPI and Reliability")
    main_path = os.path.join(base, "app", "main.py")
    main_py = read_text(main_path) if os.path.exists(main_path) else ""
    results.append(check("/health endpoint defined", '"/health"' in main_py or "'/health'" in main_py))
    results.append(check("/ready endpoint defined", '"/ready"' in main_py or "'/ready'" in main_py))
    results.append(check("/ask endpoint defined", '"/ask"' in main_py or "'/ask'" in main_py))
    results.append(check("API key authentication used", "verify_api_key" in main_py))
    results.append(check("Redis conversation history used", "history:" in main_py and "lrange" in main_py))
    results.append(check("Graceful shutdown signal handling", "SIGTERM" in main_py))
    results.append(check("Structured JSON logging", "JSONFormatter" in main_py or "json.dumps" in main_py))

    rate_path = os.path.join(base, "app", "rate_limiter.py")
    rate_py = read_text(rate_path) if os.path.exists(rate_path) else ""
    results.append(check("Redis rate limiting implemented", "zadd" in rate_py and "429" in rate_py))

    cost_path = os.path.join(base, "app", "cost_guard.py")
    cost_py = read_text(cost_path) if os.path.exists(cost_path) else ""
    results.append(check("Monthly cost guard implemented", "MonthlyCostGuard" in cost_py and "402" in cost_py))

    print("\nDocker")
    dockerfile_path = os.path.join(base, "Dockerfile")
    dockerfile = read_text(dockerfile_path) if os.path.exists(dockerfile_path) else ""
    results.append(check("Multi-stage build", "AS builder" in dockerfile and "AS runtime" in dockerfile))
    results.append(check("Non-root user", "USER agent" in dockerfile))
    results.append(check("HEALTHCHECK instruction", "HEALTHCHECK" in dockerfile))
    results.append(check("Slim base image", "slim" in dockerfile))

    compose_path = os.path.join(base, "docker-compose.yml")
    compose = read_text(compose_path) if os.path.exists(compose_path) else ""
    results.append(check("Docker Compose has agent service", "agent:" in compose))
    results.append(check("Docker Compose has redis service", "redis:" in compose))

    dockerignore_path = os.path.join(base, ".dockerignore")
    dockerignore = read_text(dockerignore_path) if os.path.exists(dockerignore_path) else ""
    results.append(check(".dockerignore covers .env", ".env" in dockerignore))
    results.append(check(".dockerignore covers __pycache__", "__pycache__" in dockerignore))

    passed = sum(1 for result in results if result["passed"])
    total = len(results)
    pct = round(passed / total * 100)

    print()
    print("=" * 55)
    print(f"  Result: {passed}/{total} checks passed ({pct}%)")
    if pct == 100:
        print("  PRODUCTION READY")
    elif pct >= 80:
        print("  Almost there. Fix the failed items above.")
    else:
        print("  Not ready yet. Review the failed items above.")
    print("=" * 55)
    print()

    return pct == 100


if __name__ == "__main__":
    sys.exit(0 if run_checks() else 1)
