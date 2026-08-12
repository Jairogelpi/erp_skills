# ruff: noqa: E501
"""Generate deterministic, self-contained 1080p SVG cards for the video."""

from __future__ import annotations

import argparse
from pathlib import Path

ASSETS = (
    "01-method.svg",
    "02-architecture.svg",
    "03-odoo-proof.svg",
    "04-results.svg",
    "05-limitations.svg",
)

BG = "#07111F"
PANEL = "#101F33"
PANEL_2 = "#162A43"
INK = "#F4F8FC"
MUTED = "#9EB2C9"
CYAN = "#42D3FF"
MINT = "#58E0B3"
AMBER = "#FFBD59"
RED = "#FF6B78"


def _base(*, number: str, title: str, subtitle: str, body: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080" role="img" aria-labelledby="title desc">
  <title id="title">{title}</title>
  <desc id="desc">{subtitle}</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{BG}"/>
      <stop offset="1" stop-color="#0C1B30"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="16" stdDeviation="22" flood-color="#000814" flood-opacity=".38"/>
    </filter>
  </defs>
  <rect width="1920" height="1080" fill="url(#bg)"/>
  <circle cx="1700" cy="-30" r="330" fill="{CYAN}" opacity=".055"/>
  <circle cx="90" cy="1010" r="260" fill="{MINT}" opacity=".045"/>
  <text x="104" y="82" fill="{CYAN}" font-family="Arial, Helvetica, sans-serif" font-size="22" font-weight="700" letter-spacing="5">ERP AGENT OS  /  {number}</text>
  <text x="104" y="164" fill="{INK}" font-family="Arial, Helvetica, sans-serif" font-size="62" font-weight="750">{title}</text>
  <text x="106" y="213" fill="{MUTED}" font-family="Arial, Helvetica, sans-serif" font-size="26">{subtitle}</text>
  {body}
  <line x1="104" y1="1008" x2="1816" y2="1008" stroke="#29405C" stroke-width="2"/>
  <text x="104" y="1048" fill="{MUTED}" font-family="Arial, Helvetica, sans-serif" font-size="19" letter-spacing="1">TFM · MÉTODO PRIMERO · EVIDENCIA CON ESTADO VISIBLE</text>
</svg>
'''


def _method() -> str:
    body = f'''
  <g filter="url(#shadow)">
    <rect x="104" y="284" width="560" height="600" rx="32" fill="{PANEL}" stroke="#203A57" stroke-width="2"/>
    <text x="152" y="342" fill="{MUTED}" font-family="Arial" font-size="22" font-weight="700" letter-spacing="3">DISEÑO PROSPECTIVO</text>
    <text x="152" y="478" fill="{INK}" font-family="Arial" font-size="116" font-weight="800">120</text>
    <text x="152" y="525" fill="{CYAN}" font-family="Arial" font-size="28" font-weight="700">PETICIONES NUEVAS</text>
    <line x1="152" y1="570" x2="616" y2="570" stroke="#2B4665" stroke-width="2"/>
    <text x="152" y="658" fill="{INK}" font-family="Arial" font-size="72" font-weight="750">24 × 5</text>
    <text x="152" y="700" fill="{MUTED}" font-family="Arial" font-size="24">intenciones × casos</text>
    <text x="152" y="790" fill="{MINT}" font-family="Arial" font-size="24" font-weight="700">AUTOR ≠ SELECTOR</text>
    <text x="152" y="832" fill="{MUTED}" font-family="Arial" font-size="21">oracle compilado después</text>
  </g>
  <g filter="url(#shadow)">
    <rect x="706" y="284" width="1110" height="600" rx="32" fill="{PANEL}" stroke="#203A57" stroke-width="2"/>
    <text x="758" y="342" fill="{MUTED}" font-family="Arial" font-size="22" font-weight="700" letter-spacing="3">UNIDAD EMPAREJADA</text>
    <g transform="translate(758 394)">
      <rect width="270" height="118" rx="22" fill="{PANEL_2}" stroke="{CYAN}" stroke-width="2"/>
      <text x="135" y="54" text-anchor="middle" fill="{INK}" font-family="Arial" font-size="42" font-weight="800">A</text>
      <text x="135" y="88" text-anchor="middle" fill="{MUTED}" font-family="Arial" font-size="19">agente directo</text>
      <rect x="304" width="270" height="118" rx="22" fill="{PANEL_2}" stroke="{AMBER}" stroke-width="2"/>
      <text x="439" y="54" text-anchor="middle" fill="{INK}" font-family="Arial" font-size="42" font-weight="800">B</text>
      <text x="439" y="88" text-anchor="middle" fill="{MUTED}" font-family="Arial" font-size="19">herramientas tipadas</text>
      <rect x="608" width="270" height="118" rx="22" fill="{PANEL_2}" stroke="{MINT}" stroke-width="2"/>
      <text x="743" y="54" text-anchor="middle" fill="{INK}" font-family="Arial" font-size="42" font-weight="800">C</text>
      <text x="743" y="88" text-anchor="middle" fill="{MUTED}" font-family="Arial" font-size="19">gobierno completo</text>
    </g>
    <text x="758" y="600" fill="{INK}" font-family="Arial" font-size="37" font-weight="700">3 sistemas × 3 repeticiones independientes</text>
    <text x="758" y="684" fill="{CYAN}" font-family="Arial" font-size="88" font-weight="850">1.080</text>
    <text x="1048" y="678" fill="{INK}" font-family="Arial" font-size="38" font-weight="700">observaciones</text>
    <text x="758" y="758" fill="{MUTED}" font-family="Arial" font-size="23">mismo modelo · rol · estado · presupuesto · evaluador</text>
    <rect x="758" y="796" width="900" height="58" rx="29" fill="#123548"/>
    <text x="1208" y="834" text-anchor="middle" fill="{CYAN}" font-family="Arial" font-size="24" font-weight="700">PRIMARIO  ·  STSR  ·  C−B  ·  IC95  ·  McNEMAR</text>
  </g>'''
    return _base(
        number="01",
        title="Primero, un experimento que pueda fallar",
        subtitle="ERP-Skills-Bench v2 · diseño previo a cualquier salida A/B/C",
        body=body,
    )


def _architecture() -> str:
    body = f'''
  <rect x="104" y="286" width="552" height="616" rx="34" fill="#10233A" stroke="{CYAN}" stroke-width="3" filter="url(#shadow)"/>
  <text x="152" y="344" fill="{CYAN}" font-family="Arial" font-size="22" font-weight="700" letter-spacing="3">ZONA PROBABILÍSTICA</text>
  <text x="152" y="420" fill="{INK}" font-family="Arial" font-size="42" font-weight="750">El modelo propone</text>
  <rect x="152" y="480" width="456" height="102" rx="20" fill="{PANEL_2}"/>
  <text x="184" y="522" fill="{INK}" font-family="Arial" font-size="25" font-weight="700">01  Interpretar intención</text>
  <text x="184" y="554" fill="{MUTED}" font-family="Arial" font-size="20">texto → propuesta tipada</text>
  <rect x="152" y="606" width="456" height="102" rx="20" fill="{PANEL_2}"/>
  <text x="184" y="648" fill="{INK}" font-family="Arial" font-size="25" font-weight="700">02  Recuperar candidatas</text>
  <text x="184" y="680" fill="{MUTED}" font-family="Arial" font-size="20">ranking o abstención</text>
  <rect x="152" y="748" width="456" height="96" rx="20" fill="#142B43" stroke="#294866"/>
  <text x="380" y="807" text-anchor="middle" fill="{MUTED}" font-family="Arial" font-size="23">SIN AUTORIDAD DE ESCRITURA</text>
  <path d="M682 592 H792" stroke="{AMBER}" stroke-width="5"/>
  <path d="M792 592 l-24 -16 v32 z" fill="{AMBER}"/>
  <rect x="814" y="286" width="1002" height="616" rx="34" fill="{PANEL}" stroke="{MINT}" stroke-width="3" filter="url(#shadow)"/>
  <text x="862" y="344" fill="{MINT}" font-family="Arial" font-size="22" font-weight="700" letter-spacing="3">ZONA DETERMINISTA</text>
  <text x="862" y="420" fill="{INK}" font-family="Arial" font-size="42" font-weight="750">El contrato decide</text>
  <g font-family="Arial">
    <rect x="862" y="482" width="264" height="122" rx="20" fill="{PANEL_2}"/><text x="994" y="532" text-anchor="middle" fill="{INK}" font-size="24" font-weight="700">VALIDAR</text><text x="994" y="568" text-anchor="middle" fill="{MUTED}" font-size="19">schema · rango</text>
    <rect x="1150" y="482" width="264" height="122" rx="20" fill="{PANEL_2}"/><text x="1282" y="532" text-anchor="middle" fill="{INK}" font-size="24" font-weight="700">POLÍTICA</text><text x="1282" y="568" text-anchor="middle" fill="{MUTED}" font-size="19">rol · riesgo</text>
    <rect x="1438" y="482" width="328" height="122" rx="20" fill="{PANEL_2}"/><text x="1602" y="532" text-anchor="middle" fill="{INK}" font-size="24" font-weight="700">APROBACIÓN</text><text x="1602" y="568" text-anchor="middle" fill="{MUTED}" font-size="19">alcance · expiración</text>
    <rect x="862" y="630" width="264" height="122" rx="20" fill="{PANEL_2}"/><text x="994" y="680" text-anchor="middle" fill="{INK}" font-size="24" font-weight="700">EJECUTAR</text><text x="994" y="716" text-anchor="middle" fill="{MUTED}" font-size="19">handler registrado</text>
    <rect x="1150" y="630" width="264" height="122" rx="20" fill="{PANEL_2}"/><text x="1282" y="680" text-anchor="middle" fill="{INK}" font-size="24" font-weight="700">VERIFICAR</text><text x="1282" y="716" text-anchor="middle" fill="{MUTED}" font-size="19">estado releído</text>
    <rect x="1438" y="630" width="328" height="122" rx="20" fill="{PANEL_2}"/><text x="1602" y="680" text-anchor="middle" fill="{INK}" font-size="24" font-weight="700">AUDITAR</text><text x="1602" y="716" text-anchor="middle" fill="{MUTED}" font-size="19">evidencia inmutable</text>
  </g>
  <rect x="862" y="790" width="904" height="64" rx="32" fill="#123B35"/>
  <text x="1314" y="831" text-anchor="middle" fill="{MINT}" font-family="Arial" font-size="25" font-weight="700">FALLA CERRADO · IDEMPOTENTE · POSTCONDICIONES EJECUTADAS</text>'''
    return _base(
        number="02",
        title="Separar comprender de ejecutar",
        subtitle="La propuesta es probabilística; la mutación queda dentro del contrato",
        body=body,
    )


def _odoo() -> str:
    body = f'''
  <rect x="104" y="278" width="1712" height="106" rx="26" fill="#322814" stroke="{AMBER}" stroke-width="2"/>
  <text x="960" y="344" text-anchor="middle" fill="{AMBER}" font-family="Arial" font-size="28" font-weight="800" letter-spacing="2">DEMOSTRACIÓN ODOO · NO RESULTADO EXPERIMENTAL A/B/C</text>
  <line x1="230" y1="626" x2="1690" y2="626" stroke="#31506F" stroke-width="8"/>
  <g font-family="Arial">
    <circle cx="300" cy="626" r="42" fill="{MINT}"/><text x="300" y="638" text-anchor="middle" fill="{BG}" font-size="30" font-weight="800">1</text>
    <text x="300" y="502" text-anchor="middle" fill="{INK}" font-size="31" font-weight="750">R1 ejecuta</text><text x="300" y="548" text-anchor="middle" fill="{MUTED}" font-size="21">bajo impacto</text>
    <rect x="166" y="700" width="268" height="72" rx="18" fill="#123B35"/><text x="300" y="744" text-anchor="middle" fill="{MINT}" font-size="22" font-weight="700">RELECTURA ✓</text>
    <circle cx="740" cy="626" r="42" fill="{AMBER}"/><text x="740" y="638" text-anchor="middle" fill="{BG}" font-size="30" font-weight="800">2</text>
    <text x="740" y="502" text-anchor="middle" fill="{INK}" font-size="31" font-weight="750">R2 se bloquea</text><text x="740" y="548" text-anchor="middle" fill="{MUTED}" font-size="21">falta aprobación</text>
    <rect x="586" y="700" width="308" height="72" rx="18" fill="#3A2917"/><text x="740" y="744" text-anchor="middle" fill="{AMBER}" font-size="21" font-weight="700">SIN CAMBIO ✓</text>
    <circle cx="1180" cy="626" r="42" fill="{CYAN}"/><text x="1180" y="638" text-anchor="middle" fill="{BG}" font-size="30" font-weight="800">3</text>
    <text x="1180" y="502" text-anchor="middle" fill="{INK}" font-size="31" font-weight="750">Aprobación</text><text x="1180" y="548" text-anchor="middle" fill="{MUTED}" font-size="21">actor · alcance · tiempo</text>
    <rect x="1026" y="700" width="308" height="72" rx="18" fill="#113347"/><text x="1180" y="744" text-anchor="middle" fill="{CYAN}" font-size="21" font-weight="700">TRAZA ✓</text>
    <circle cx="1620" cy="626" r="42" fill="{MINT}"/><text x="1620" y="638" text-anchor="middle" fill="{BG}" font-size="30" font-weight="800">4</text>
    <text x="1620" y="502" text-anchor="middle" fill="{INK}" font-size="31" font-weight="750">R2 ejecuta</text><text x="1620" y="548" text-anchor="middle" fill="{MUTED}" font-size="21">mismo contrato</text>
    <rect x="1472" y="700" width="296" height="72" rx="18" fill="#123B35"/><text x="1620" y="744" text-anchor="middle" fill="{MINT}" font-size="22" font-weight="700">RELECTURA ✓</text>
  </g>
  <text x="960" y="868" text-anchor="middle" fill="{MUTED}" font-family="Arial" font-size="24">Una toma continua · datos sintéticos · instancia de desarrollo · sin R4</text>'''
    return _base(
        number="03",
        title="La demo prueba la tubería, no la hipótesis",
        subtitle="Aprobación y verificación independiente sobre Odoo 19",
        body=body,
    )


def _results() -> str:
    body = f'''
  <rect x="104" y="276" width="1712" height="168" rx="32" fill="#332715" stroke="{AMBER}" stroke-width="3" filter="url(#shadow)"/>
  <text x="154" y="330" fill="{AMBER}" font-family="Arial" font-size="21" font-weight="800" letter-spacing="4">RESULTADO PRIMARIO</text>
  <text x="154" y="397" fill="{INK}" font-family="Arial" font-size="58" font-weight="850">V2 PENDIENTE</text>
  <text x="770" y="386" fill="{MUTED}" font-family="Arial" font-size="26">sin dataset + freeze + 1.080 observaciones válidas</text>
  <rect x="104" y="488" width="1712" height="414" rx="32" fill="{PANEL}" stroke="#203A57" stroke-width="2" filter="url(#shadow)"/>
  <rect x="144" y="526" width="258" height="46" rx="23" fill="#123548"/>
  <text x="273" y="557" text-anchor="middle" fill="{CYAN}" font-family="Arial" font-size="20" font-weight="800" letter-spacing="2">EXPLORATORIO V1</text>
  <text x="144" y="630" fill="{MUTED}" font-family="Arial" font-size="21" font-weight="700">STSR · baseline tipado B</text>
  <rect x="144" y="662" width="520" height="58" rx="15" fill="#21364D"/>
  <rect x="144" y="662" width="251" height="58" rx="15" fill="{AMBER}"/>
  <text x="694" y="703" fill="{INK}" font-family="Arial" font-size="36" font-weight="800">0,483</text>
  <text x="144" y="782" fill="{MUTED}" font-family="Arial" font-size="21" font-weight="700">STSR · ERP Agent OS C</text>
  <rect x="144" y="814" width="520" height="58" rx="15" fill="#21364D"/>
  <rect x="144" y="814" width="329" height="58" rx="15" fill="{MINT}"/>
  <text x="694" y="855" fill="{INK}" font-family="Arial" font-size="36" font-weight="800">0,633</text>
  <line x1="850" y1="574" x2="850" y2="850" stroke="#2B4665" stroke-width="2"/>
  <text x="912" y="635" fill="{MUTED}" font-family="Arial" font-size="21" font-weight="700">OTRAS SEÑALES EXPLORATORIAS</text>
  <text x="912" y="711" fill="{INK}" font-family="Arial" font-size="31" font-weight="750">false allow</text>
  <text x="1240" y="711" fill="{AMBER}" font-family="Arial" font-size="31" font-weight="800">0,889</text>
  <text x="1432" y="711" fill="{MUTED}" font-family="Arial" font-size="24">→</text>
  <text x="1516" y="711" fill="{MINT}" font-family="Arial" font-size="31" font-weight="800">0,111</text>
  <text x="912" y="793" fill="{INK}" font-family="Arial" font-size="31" font-weight="750">tokens / ejecución</text>
  <text x="1240" y="793" fill="{AMBER}" font-family="Arial" font-size="31" font-weight="800">265,3</text>
  <text x="1432" y="793" fill="{MUTED}" font-family="Arial" font-size="24">→</text>
  <text x="1516" y="793" fill="{MINT}" font-family="Arial" font-size="31" font-weight="800">67,6</text>
  <text x="912" y="858" fill="{MUTED}" font-family="Arial" font-size="19">señal para justificar v2 · no conclusión final</text>'''
    return _base(
        number="04",
        title="No rellenar el hueco con una cifra antigua",
        subtitle="La separación entre estados de evidencia también debe verse",
        body=body,
    )


def _limitations() -> str:
    body = f'''
  <rect x="104" y="278" width="660" height="606" rx="34" fill="#2B1722" stroke="{RED}" stroke-width="3" filter="url(#shadow)"/>
  <text x="154" y="336" fill="{RED}" font-family="Arial" font-size="21" font-weight="800" letter-spacing="3">RESULTADO NEGATIVO</text>
  <text x="154" y="510" fill="{INK}" font-family="Arial" font-size="126" font-weight="850">3,3 %</text>
  <text x="154" y="568" fill="{INK}" font-family="Arial" font-size="31" font-weight="750">detección externa</text>
  <text x="154" y="618" fill="{MUTED}" font-family="Arial" font-size="23">InjecAgent · detector léxico</text>
  <line x1="154" y1="670" x2="714" y2="670" stroke="#5A2C3A" stroke-width="2"/>
  <text x="154" y="728" fill="{MUTED}" font-family="Arial" font-size="21">Reconocer patrones conocidos</text>
  <text x="154" y="762" fill="{MUTED}" font-family="Arial" font-size="21">no equivale a contener acciones.</text>
  <rect x="154" y="804" width="310" height="48" rx="24" fill="#4B1E2B"/>
  <text x="309" y="836" text-anchor="middle" fill="{RED}" font-family="Arial" font-size="19" font-weight="800">NO SE OCULTA</text>
  <rect x="808" y="278" width="1008" height="286" rx="34" fill="{PANEL}" stroke="{CYAN}" stroke-width="2" filter="url(#shadow)"/>
  <text x="858" y="336" fill="{CYAN}" font-family="Arial" font-size="20" font-weight="800" letter-spacing="3">STRESS EXPLORATORIO · CONFINAMIENTO POR TRES CANALES</text>
  <text x="858" y="458" fill="{INK}" font-family="Arial" font-size="86" font-weight="850">0 / 1.530</text>
  <rect x="1440" y="410" width="320" height="58" rx="29" fill="#3B2618"/>
  <text x="1600" y="448" text-anchor="middle" fill="{AMBER}" font-family="Arial" font-size="21" font-weight="800">NO ADAPTATIVO</text>
  <text x="858" y="518" fill="{MUTED}" font-family="Arial" font-size="20">observado en ese alcance · no certificación</text>
  <rect x="808" y="606" width="1008" height="278" rx="34" fill="{PANEL}" stroke="#203A57" stroke-width="2" filter="url(#shadow)"/>
  <text x="858" y="664" fill="{MUTED}" font-family="Arial" font-size="21" font-weight="800" letter-spacing="3">LÍMITES DE TRANSFERENCIA</text>
  <g font-family="Arial" font-size="24" fill="{INK}">
    <text x="858" y="728">• datos sintéticos y español</text>
    <text x="858" y="778">• 12 skills · Odoo limitado a demo</text>
    <text x="858" y="828">• sin usuarios reales ni ahorro observado</text>
    <text x="1320" y="728">• sin segundo anotador humano</text>
    <text x="1320" y="778">• audit IA ≠ acuerdo humano</text>
    <text x="1320" y="828">• v2 todavía pendiente</text>
  </g>'''
    return _base(
        number="05",
        title="El límite también es un resultado",
        subtitle="Transferencia, adversarios y evidencia que todavía falta",
        body=body,
    )


def make_assets(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = (_method(), _architecture(), _odoo(), _results(), _limitations())
    for name, payload in zip(ASSETS, payloads, strict=True):
        (output_dir / name).write_text(payload, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("reports") / "video")
    args = parser.parse_args(argv)
    make_assets(args.output_dir)
    print(f"generated {len(ASSETS)} deterministic 1080p SVG assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
