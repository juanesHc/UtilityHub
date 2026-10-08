import type { Torre } from '../../api/tipos'
import { formatearNumero, formatearPeriodoLargo, pluralizar } from '../../dominio/formato'
import type { AnalisisCsv } from '../../dominio/analisisCsv'

interface PropiedadesVistaPrevia {
  nombreArchivo: string
  tamanoBytes: number
  analisis: AnalisisCsv
  torres: Torre[]
  onSubir: () => void
  onCancelar: () => void
}

function formatearTamano(tamanoBytes: number): string {
  if (tamanoBytes < 1024) {
    return `${tamanoBytes} B`
  }
  if (tamanoBytes < 1024 * 1024) {
    return `${formatearNumero(tamanoBytes / 1024, 1)} KB`
  }
  return `${formatearNumero(tamanoBytes / (1024 * 1024), 1)} MB`
}

export function VistaPreviaCsv({ nombreArchivo, tamanoBytes, analisis, torres, onSubir, onCancelar }: PropiedadesVistaPrevia) {
  const { identificacion } = analisis
  const torre = identificacion === null ? undefined : torres.find((candidata) => candidata.codigo === identificacion.codigoTorre)
  const torreDesconocida = identificacion !== null && torres.length > 0 && torre === undefined
  const problemas = torreDesconocida
    ? [`La torre ${identificacion.codigoTorre} no está registrada.`, ...analisis.problemas]
    : analisis.problemas
  const columnas = analisis.encabezado.length

  return (
    <div className="vista-previa">
      <p className="subida__archivo">{nombreArchivo}</p>
      <dl className="vista-previa__datos">
        <div className="vista-previa__dato">
          <dt>Torre</dt>
          <dd>{torre?.nombre ?? identificacion?.codigoTorre ?? '—'}</dd>
        </div>
        <div className="vista-previa__dato">
          <dt>Periodo</dt>
          <dd>{identificacion === null ? '—' : formatearPeriodoLargo(identificacion.periodo)}</dd>
        </div>
        <div className="vista-previa__dato">
          <dt>Filas de lecturas</dt>
          <dd>{formatearNumero(analisis.totalFilas, 0)}</dd>
        </div>
        <div className="vista-previa__dato">
          <dt>Tamaño</dt>
          <dd>{formatearTamano(tamanoBytes)}</dd>
        </div>
      </dl>

      {problemas.length > 0 && (
        <ul className="vista-previa__avisos vista-previa__avisos--problema" role="alert">
          {problemas.map((problema) => (
            <li key={problema}>{problema}</li>
          ))}
        </ul>
      )}
      {analisis.avisos.length > 0 && (
        <ul className="vista-previa__avisos">
          {analisis.avisos.map((aviso) => (
            <li key={aviso}>{aviso}</li>
          ))}
        </ul>
      )}

      {columnas > 0 && analisis.filasMuestra.length > 0 && (
        <div className="vista-previa__tabla-contenedor">
          <table className="vista-previa__tabla">
            <caption>
              {analisis.filasMuestra.length < analisis.totalFilas
                ? `Primeras ${analisis.filasMuestra.length} de ${formatearNumero(analisis.totalFilas, 0)} filas`
                : `${analisis.totalFilas} ${pluralizar(analisis.totalFilas, 'fila', 'filas')}`}
            </caption>
            <thead>
              <tr>
                {analisis.encabezado.map((columna, indice) => (
                  <th key={`${columna}-${indice}`} scope="col">
                    {columna}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {analisis.filasMuestra.map((fila, indiceFila) => (
                <tr key={indiceFila}>
                  {Array.from({ length: columnas }, (_, indiceColumna) => (
                    <td key={indiceColumna}>{fila[indiceColumna] ?? ''}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="vista-previa__nota">
        Esta vista solo revisa el nombre, el tamaño y el encabezado. Las lecturas se validan al procesar el archivo.
      </p>
      <div className="vista-previa__acciones">
        <button type="button" className="subida__boton" disabled={problemas.length > 0} onClick={onSubir}>
          Subir archivo
        </button>
        <button type="button" className="vista-previa__cancelar" onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </div>
  )
}
