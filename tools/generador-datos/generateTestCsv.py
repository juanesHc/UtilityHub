import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path


TORRES = [1, 2, 3]
PISOS_POR_TORRE = 5
APARTAMENTOS_POR_PISO = 4

PERIODO_INICIAL = (2025, 10)
NUMERO_PERIODOS = 12

SERVICIOS = {
    "AGUA": {"minimo": 8.0, "maximo": 18.0, "decimales": 1, "acumulado_inicial": (400, 2500)},
    "ENERGIA": {"minimo": 120.0, "maximo": 350.0, "decimales": 0, "acumulado_inicial": (5000, 40000)},
}

ESTACIONALIDAD = {
    "AGUA": {1: 1.10, 2: 1.12, 3: 1.08, 4: 0.95, 5: 0.92, 6: 0.95,
             7: 1.05, 8: 1.08, 9: 0.98, 10: 0.92, 11: 0.90, 12: 1.00},
    "ENERGIA": {1: 1.05, 2: 1.02, 3: 1.00, 4: 0.98, 5: 0.97, 6: 0.98,
                7: 1.00, 8: 1.02, 9: 1.00, 10: 0.98, 11: 1.00, 12: 1.08},
}

VARIACION_MENSUAL = 0.12       
ANOMALIAS_A_INYECTAR = 6       
FACTOR_ANOMALIA = (2.5, 4.0)   


ERRORES = {
    "duplicado": 3,    
    "incompleto": 3,    
    "formato": 3,       
    "retroceso": 2,     
}

ENCABEZADO = ["torre", "apartamento", "servicio", "periodo", "lectura_acumulada", "fecha_lectura"]


def construir_periodos(inicio, cantidad):

    anio, mes = inicio
    periodos = []
    for _ in range(cantidad):
        periodos.append((anio, mes))
        mes += 1
        if mes > 12:
            mes = 1
            anio += 1
    return periodos


def etiqueta_periodo(periodo):
    return "{:04d}-{:02d}".format(periodo[0], periodo[1])


def fecha_de_lectura(periodo, azar):
    anio, mes = periodo
    if mes == 12:
        siguiente = date(anio + 1, 1, 1)
    else:
        siguiente = date(anio, mes + 1, 1)
    return siguiente + timedelta(days=azar.randint(0, 4))


def codigo_apartamento(piso, posicion):
    return piso * 100 + posicion


def construir_apartamentos():
    apartamentos = []
    for torre in TORRES:
        for piso in range(1, PISOS_POR_TORRE + 1):
            for posicion in range(1, APARTAMENTOS_POR_PISO + 1):
                apartamentos.append((torre, codigo_apartamento(piso, posicion)))
    return apartamentos



def generar_series(apartamentos, periodos, azar):

    series = {}
    for torre, apartamento in apartamentos:
        for servicio, ajustes in SERVICIOS.items():
            base = azar.uniform(ajustes["minimo"], ajustes["maximo"])
            acumulado = float(azar.randint(*ajustes["acumulado_inicial"]))
            filas = []
            for periodo in periodos:
                factor = ESTACIONALIDAD[servicio][periodo[1]]
                ruido = azar.uniform(1 - VARIACION_MENSUAL, 1 + VARIACION_MENSUAL)
                consumo = base * factor * ruido
                acumulado += consumo
                filas.append({
                    "periodo": periodo,
                    "consumo": consumo,
                    "acumulado": acumulado,
                    "anomalo": False,
                })
            series[(torre, apartamento, servicio)] = filas
    return series


def nombre_archivo(torre, periodo):

    return "lecturas_T{:02d}_{}.csv".format(torre, etiqueta_periodo(periodo))


def inyectar_anomalias(series, azar):

    casos = []
    claves = list(series.keys())
    elegidas = azar.sample(claves, min(ANOMALIAS_A_INYECTAR, len(claves)))

    for clave in elegidas:
        filas = series[clave]

        indice = azar.randint(3, len(filas) - 1)
        factor = azar.uniform(*FACTOR_ANOMALIA)
        exceso = filas[indice]["consumo"] * (factor - 1)

        filas[indice]["consumo"] *= factor
        filas[indice]["anomalo"] = True
        for posterior in filas[indice:]:
            posterior["acumulado"] += exceso

        torre, apartamento, servicio = clave
        periodo = filas[indice]["periodo"]
        casos.append({
            "tipo": "anomalia",
            "archivo": nombre_archivo(torre, periodo),
            "torre": "T{:02d}".format(torre),
            "apartamento": apartamento,
            "servicio": servicio,
            "periodo": etiqueta_periodo(periodo),
            "detalle": "consumo {:.1f} veces el esperado".format(factor),
        })
    return casos


def formatear(valor, servicio):
    decimales = SERVICIOS[servicio]["decimales"]
    return "{:.{}f}".format(valor, decimales)


def construir_filas(series, torre, periodo):

    filas = []
    for (t, apartamento, servicio), registros in series.items():
        if t != torre:
            continue
        for registro in registros:
            if registro["periodo"] != periodo:
                continue
            filas.append({
                "torre": "T{:02d}".format(torre),
                "apartamento": apartamento,
                "servicio": servicio,
                "periodo": etiqueta_periodo(periodo),
                "lectura_acumulada": formatear(registro["acumulado"], servicio),
                "fecha_lectura": "",
                "_servicio": servicio,
            })
    filas.sort(key=lambda f: (f["apartamento"], f["_servicio"]))
    return filas


def planificar_errores(archivos, azar):

    sufijo_base = "_{}.csv".format(etiqueta_periodo(PERIODO_INICIAL))
    candidatos = [nombre for nombre in archivos if not nombre.endswith(sufijo_base)]
    if not candidatos:
        candidatos = list(archivos)

    plan = {}
    for tipo, cantidad in ERRORES.items():
        for _ in range(cantidad):
            archivo = azar.choice(candidatos)
            plan.setdefault(archivo, []).append(tipo)
    return plan


def aplicar_errores(filas, tipos, azar, anterior_por_clave, archivo):
    casos = []
    for tipo in tipos:
        if not filas:
            break
        indice = azar.randrange(len(filas))
        fila = filas[indice]
        base = {
            "archivo": archivo,
            "torre": fila["torre"],
            "apartamento": fila["apartamento"],
            "servicio": fila["servicio"],
            "periodo": fila["periodo"],
        }

        if tipo == "duplicado":
            filas.insert(indice + 1, dict(fila))
            casos.append(dict(base, tipo="duplicado", detalle="la fila aparece dos veces"))

        elif tipo == "incompleto":
            fila["lectura_acumulada"] = ""
            casos.append(dict(base, tipo="incompleto", detalle="lectura_acumulada vacia"))

        elif tipo == "formato":
            fila["lectura_acumulada"] = azar.choice(["N/D", "ilegible", "12,5,8"])
            casos.append(dict(base, tipo="formato", detalle="valor no numerico"))

        elif tipo == "retroceso":
            clave = (fila["torre"], fila["apartamento"], fila["servicio"])
            previo = anterior_por_clave.get(clave)
            if previo is None:
                continue
            valor = float(previo) * azar.uniform(0.80, 0.95)
            fila["lectura_acumulada"] = formatear(valor, fila["servicio"])
            casos.append(dict(base, tipo="retroceso", detalle="lectura menor que la anterior"))

    return casos


def escribir(series, periodos, destino, azar):
    destino.mkdir(parents=True, exist_ok=True)

    nombres = []
    contenido = {}
    anterior_por_clave = {}

    for periodo in periodos:
        for torre in TORRES:
            nombre = nombre_archivo(torre, periodo)
            filas = construir_filas(series, torre, periodo)
            for fila in filas:
                fila["fecha_lectura"] = fecha_de_lectura(periodo, azar).isoformat()
            nombres.append(nombre)
            contenido[nombre] = filas

    plan = planificar_errores(nombres, azar)
    casos = []

    for nombre in nombres:
        filas = contenido[nombre]
        if nombre in plan:
            casos.extend(aplicar_errores(filas, plan[nombre], azar, anterior_por_clave, nombre))

        for fila in filas:
            clave = (fila["torre"], fila["apartamento"], fila["servicio"])
            if fila["lectura_acumulada"] not in ("",) and not fila["lectura_acumulada"][0].isalpha():
                try:
                    anterior_por_clave[clave] = float(fila["lectura_acumulada"])
                except ValueError:
                    pass

        with open(destino / nombre, "w", newline="", encoding="utf-8") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=ENCABEZADO, extrasaction="ignore")
            escritor.writeheader()
            escritor.writerows(filas)

    return nombres, casos


def escribir_manifiesto(destino, casos):
    columnas = ["tipo", "archivo", "torre", "apartamento", "servicio", "periodo", "detalle"]
    ruta = destino / "casos_esperados.csv"
    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas, extrasaction="ignore")
        escritor.writeheader()
        for caso in sorted(casos, key=lambda c: (c["tipo"], c["archivo"], str(c["apartamento"]))):
            escritor.writerow(caso)
    return ruta



def main():
    analizador = argparse.ArgumentParser(description="Genera lecturas simuladas para UtilityHub.")
    analizador.add_argument("--semilla", type=int, default=42,
                            help="semilla del generador; la misma semilla produce los mismos datos")
    analizador.add_argument("--salida", type=Path, default=Path("salida"),
                            help="carpeta donde se escriben los CSV")
    argumentos = analizador.parse_args()

    azar = random.Random(argumentos.semilla)

    periodos = construir_periodos(PERIODO_INICIAL, NUMERO_PERIODOS)
    apartamentos = construir_apartamentos()

    series = generar_series(apartamentos, periodos, azar)
    casos = inyectar_anomalias(series, azar)

    nombres, casos_error = escribir(series, periodos, argumentos.salida, azar)
    casos.extend(casos_error)
    ruta_manifiesto = escribir_manifiesto(argumentos.salida, casos)

    print("Archivos generados: {}".format(len(nombres)))
    print("Apartamentos: {} | Servicios: {} | Periodos: {}".format(
        len(apartamentos), len(SERVICIOS), len(periodos)))
    print("Primer periodo (linea base): {}".format(etiqueta_periodo(periodos[0])))
    print("Casos inyectados: {} (ver {})".format(len(casos), ruta_manifiesto.name))


main()