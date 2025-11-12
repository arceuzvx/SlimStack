# SlimStack
A cross-language CLI utility to analyze, clean, and optimize your developer stack — Python, Node.js, and Docker — helping you reclaim space, speed up builds, and streamline your setup.

## 🚀 Overview

SlimStack scans your system or project directory to find unused dependencies, redundant global modules, and bloated Dockerfiles, then provides actionable suggestions or automated cleanup options.

It’s built for developers who want to reduce clutter, improve performance, and enforce clean environments — all from one CLI tool.

## ⚙️ Features

🔍 Dependency Scanner – Identify unused Python & Node packages

🧰 Global Module Audit – Detect global modules not used by any project

🧼 Safe Cleaner – Remove unnecessary packages with confirmation

🐳 Dockerfile Optimizer – Analyze and rewrite Dockerfiles for:

- Smaller base images

- Fewer layers

- Security hardening

- Build caching improvements

## Usage
```bash
# Scan all projects
python cli.py scan "C:\path\to\projects"

# Scan only Python dependencies
python cli.py scan "C:\path\to\projects" --py

# Scan only Node.js dependencies
python cli.py scan "C:\path\to\projects" --node

# Clean unused packages
python cli.py clean "C:\path\to\projects"

# Optimize Dockerfiles
python cli.py optimize-docker "C:\path\to\projects" [--auto]
```

## 🧠 Goals / Future Scope

SlimStack is designed as a modular, extensible tool that will evolve over time.
Here’s what’s planned for upcoming phases:

| Phase                                | Goal            | Description                                                |
| ------------------------------------ | --------------- | ---------------------------------------------------------- |
| **1. CLI Foundation**                | ✅ Current phase | Python & Node.js cleanup, safe deletion, rich output       |
| **2. Docker Optimization**           | In progress     | Intelligent Dockerfile rewrites, best-practice enforcement |
| **3. Virtual Environment Awareness** | Planned         | Detect & manage per-project `venv`/`env` environments      |
| **4. GUI Mode**                      | Future          | Lightweight desktop UI for visual dependency insights      |
| **5. Language Expansion**            | Future          | Add Go, Rust, and Java package managers                    |
| **6. Cloud Integration**             | Future          | Analyze Docker images directly from registries             |
| **7. AI Optimization Assistant**     | Vision          | LLM-assisted environment tuning & configuration advice     |

## 🧩 Tech Stack

Python 3.10+

Rich – for CLI visuals

Typer – for subcommands and flag parsing

Node.js – for scanning JS projects

Docker CLI – for Dockerfile analysis

## 📄 License

MIT License © 2025 Shreya Dutta
