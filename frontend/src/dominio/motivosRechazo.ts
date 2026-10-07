import type { MotivoRechazo } from '../api/tipos'

export interface ExplicacionMotivo {
  titulo: string
  comoCorregir: string
}

const EXPLICACION_POR_MOTIVO: Record<MotivoRechazo, ExplicacionMotivo> = {
  columnas_sobrantes: {
    titulo: 'La fila tiene más columnas que el encabezado',
    comoCorregir:
      'Busca comas de más. Un decimal escrito con coma y sin comillas (por ejemplo 516,0) parte el valor en dos columnas: usa punto o pon el valor entre comillas.',
  },
  campo_obligatorio_faltante: {
    titulo: 'Falta un campo obligatorio',
    comoCorregir:
      'Completa todas las columnas de la fila: torre, apartamento, servicio, periodo, lectura y fecha. El sistema no registra cuál era el campo vacío.',
  },
  tripleta_repetida_en_archivo: {
    titulo: 'Fila repetida en el archivo',
    comoCorregir:
      'El mismo apartamento, servicio y periodo aparece más de una vez, así que se rechazan todas las copias. Deja una sola fila con la lectura correcta.',
  },
  torre_distinta_a_la_del_archivo: {
    titulo: 'La torre de la fila no coincide con la del archivo',
    comoCorregir: 'Cada archivo es de una sola torre. Corrige el código de torre o mueve la fila al archivo de su torre.',
  },
  periodo_distinto_al_del_archivo: {
    titulo: 'El periodo de la fila no coincide con el del archivo',
    comoCorregir: 'Cada archivo es de un solo periodo. Corrige el periodo de las filas o el nombre del archivo.',
  },
  lectura_no_numerica: {
    titulo: 'La lectura del medidor no es un número',
    comoCorregir: 'Escribe solo el número que marca el medidor, con punto o coma decimal y sin texto ni unidades.',
  },
  lectura_fuera_de_rango: {
    titulo: 'Lectura fuera de rango',
    comoCorregir: 'La lectura debe ser mayor o igual a 0 y tener como máximo 3 decimales.',
  },
  fecha_lectura_invalida: {
    titulo: 'Fecha de lectura inválida',
    comoCorregir: 'Usa el formato AAAA-MM-DD con una fecha que exista, por ejemplo 2026-10-03.',
  },
  apartamento_inexistente: {
    titulo: 'El apartamento no existe en esta torre',
    comoCorregir: 'Revisa el número del apartamento: debe estar registrado en la torre del archivo.',
  },
  servicio_inexistente: {
    titulo: 'Servicio desconocido',
    comoCorregir: 'Usa uno de los códigos de servicio registrados, por ejemplo AGUA o ENERGIA.',
  },
  lectura_menor_que_la_anterior: {
    titulo: 'Lectura menor que la anterior: un medidor no retrocede',
    comoCorregir:
      'Verifica la lectura contra el medidor. Si es correcta porque el medidor se cambió, hay que registrar el cambio antes de volver a cargar el archivo.',
  },
}

export function explicarMotivo(motivo: MotivoRechazo): ExplicacionMotivo {
  return EXPLICACION_POR_MOTIVO[motivo]
}
