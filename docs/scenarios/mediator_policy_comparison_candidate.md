# Candidato de comparación explícita de políticas con mediación

Issue: [#1531](https://github.com/Voxterrae/HUB_Optimus/issues/1531)

Estado: candidato experimental; no es un benchmark.

## Decisión y alcance

El input canónico es
[`mediator_policy_comparison_es.json`](../../scenarios/candidates/mediator_policy_comparison_es.json).
Contiene dos partes negociadoras y una mediación externa. El título, la
descripción y los nombres están en español; `negotiator` y `mediator` se
mantienen como identificadores técnicos del runtime.

La comparación usa:

- el mismo criterio exacto, `offer: 5`;
- el mismo presupuesto de cinco rondas;
- las semillas enteras de 0 a 999, ambas incluidas;
- la política `uniform`;
- la política `biased`; y
- un control derivado que elimina el rol `mediator` sin cambiar el criterio ni
  el presupuesto de rondas.

El control sin mediador se construye solo en memoria durante la reproducción.
No es un segundo escenario canónico ni se añade al catálogo.

## Límite del runtime

El JSON no selecciona una política. `uniform` asigna a todos los roles ofertas
uniformes entre 1 y 5. `biased` mantiene ese rango para `negotiator` y limita
`mediator` al rango 2-4.

Por tanto, `biased` es aquí una restricción del rango según el rol. No codifica
preferencia por una parte, neutralidad, calidad de mediación, capacidad de
garantía ni influencia política.

El runtime marca éxito cuando cualquier actor emite exactamente `offer: 5`.
No comprueba consenso, ratificación, estabilidad, cumplimiento ni acuerdo
duradero.

## Procedencia ejecutable

La observación se generó sobre `main`
`906d3e47df48dceac2b4abd25fe81c15b9a7b235`, con Python 3.12.13.

| Entrada ejecutable | SHA-256 |
| --- | --- |
| `scenarios/candidates/mediator_policy_comparison_es.json` | `d0af7d755ce1018a966bc8a6e162f4670e1577adf7a3f052b06e57a2f2bf6c38` |
| `run_scenario.py` | `4e69d869104cdc324fb2303b933d66a84abea5252ffd2a44593c9c8b891181ee` |
| `hub_optimus_simulator.py` | `df00f950f12c08a76a6f54769818313712a9ef292b6f463485a96ca5fa0553bb` |
| `scenario.schema.json` | `983aa24429c302cff706d26c95c77306e5b44c0b91f9736c9251543a4259bde6` |

## Reproducción

Ejecutar desde la raíz del repositorio. La carga siguiente usa la puerta de
entrada autoritativa y, por tanto, valida el JSON contra el schema y las
invariantes de identidad:

```bash
python - <<'PY'
from pathlib import Path
from run_scenario import load_validated_scenario

path = Path("scenarios/candidates/mediator_policy_comparison_es.json")
load_validated_scenario(path)
print("input validado")
PY
```

Las dos políticas se seleccionan explícitamente en el CLI. Estos comandos
reproducen la semilla 42 sin añadir resultados al catálogo:

```bash
python run_scenario.py \
  scenarios/candidates/mediator_policy_comparison_es.json \
  --seed 42 --policy uniform --output /tmp/mediator-uniform-42.json

python run_scenario.py \
  scenarios/candidates/mediator_policy_comparison_es.json \
  --seed 42 --policy biased --output /tmp/mediator-biased-42.json
```

Este comando reproduce las cuatro configuraciones (dos políticas por cada
composición de actores) sobre las 1.000 semillas. Usa el input ya validado y el
mismo `Simulator` que invoca el CLI:

```bash
python - <<'PY'
from statistics import fmean
from pathlib import Path

from hub_optimus_simulator import Scenario, Simulator
from run_scenario import load_validated_scenario

path = Path("scenarios/candidates/mediator_policy_comparison_es.json")
candidate = load_validated_scenario(path)
without_mediator = Scenario(
    title=candidate.title,
    description=candidate.description,
    roles=[role for role in candidate.roles if role["role"] != "mediator"],
    success_criteria=candidate.success_criteria,
    max_rounds=candidate.max_rounds,
)

controls = {
    "con_mediador": candidate,
    "sin_mediador": without_mediator,
}
for control_name, scenario in controls.items():
    for policy_name in ("uniform", "biased"):
        results = [
            Simulator(scenario, policy_name=policy_name).run(seed=seed)
            for seed in range(1000)
        ]
        successes = [result for result in results if result["status"] == "success"]
        print(
            control_name,
            policy_name,
            f"{len(successes)}/1000",
            f"{fmean(result['rounds'] for result in successes):.6f}",
            results[42]["status"],
            results[42]["rounds"],
        )
PY
```

## Resultados observados

La media de ronda usa solo ejecuciones con éxito; su denominador es el número
de éxitos mostrado en la misma fila.

| Control | Política explícita | Éxitos / 1.000 | Media de ronda entre éxitos | Semilla 42 |
| --- | --- | ---: | ---: | --- |
| Con mediador | `uniform` | 963 / 1.000 | 1,854621 | éxito, ronda 3 |
| Con mediador | `biased` | 893 / 1.000 | 2,194849 | éxito, ronda 4 |
| Sin mediador | `uniform` | 902 / 1.000 | 2,230599 | éxito, ronda 4 |
| Sin mediador | `biased` | 902 / 1.000 | 2,230599 | éxito, ronda 4 |

**Resultado verificado:** en este conjunto enumerado, el control con mediador
obtiene menos éxitos y una ronda media condicional posterior con `biased` que
con `uniform`.

**Resultado verificado:** al retirar el mediador, `uniform` y `biased` producen
el mismo resumen. Los dos roles restantes usan el rango 1-5 bajo ambas
políticas.

**Inferencia limitada:** la dirección observada es coherente con que el
mediador no puede emitir la oferta objetivo bajo `biased`. Añadir o retirar un
actor también cambia cuántos valores consume el generador aleatorio; esta
comparación no separa ese efecto.

**Incertidumbre:** las semillas 0-999 son una enumeración determinista del
prototipo, no una muestra de negociaciones reales. La media condicionada al
éxito no describe las ejecuciones fallidas. Los resultados no establecen
causalidad, calidad de política, calidad de mediación, favoritismo, probabilidad
real ni capacidad predictiva.

## Estado de promoción

El candidato queda fuera de `benchmarks/`. No hay output esperado congelado y
este cambio no modifica el simulador, el runner, el schema ni CI. Cualquier
promoción posterior requiere la decisión separada y la revisión de zona
protegida descritas en [#1536](https://github.com/Voxterrae/HUB_Optimus/issues/1536).
