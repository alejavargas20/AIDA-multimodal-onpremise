# Git Workflow del Proyecto

## Ramas principales
- **main** → estable, protegida.
- **develop** → integración con el equipo.

## Ramas feature
Cada desarrollador crea sus ramas así:
```
git checkout -b feature/<nombre-del-modulo>
```

Ejemplos:
- feature/orchestrator-core
- feature/nlp-agent
- feature/prompt-optimizer

## Flujo de trabajo
1. Crear rama desde develop.
2. Trabajar en tu rama.
3. Hacer commit y push.
4. Crear Pull Request hacia develop.
5. Esperar revisión.
6. Hacer merge solo después de aprobación.

## Que no hacer:
- No trabajar en main.
- No trabajar directamente en develop.
- No subir binarios, datasets, venv, etc.

## Reglas del PR
- Mínimo un revisor.
- Descripción clara.
- No romper develop.

