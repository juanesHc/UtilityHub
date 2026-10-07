import './paginacion.css'

interface PropiedadesPaginacion {
  paginaActual: number
  totalPaginas: number
  alCambiarPagina: (pagina: number) => void
  etiqueta: string
}

type ElementoPaginacion = number | 'separador-inicial' | 'separador-final'

const PAGINAS_VISIBLES_ALREDEDOR = 3

function calcularElementos(paginaActual: number, totalPaginas: number): ElementoPaginacion[] {
  const inicioVentana = Math.max(1, Math.min(paginaActual - 1, totalPaginas - PAGINAS_VISIBLES_ALREDEDOR + 1))
  const finVentana = Math.min(totalPaginas, inicioVentana + PAGINAS_VISIBLES_ALREDEDOR - 1)
  const elementos: ElementoPaginacion[] = []
  if (inicioVentana > 1) {
    elementos.push(1)
    if (inicioVentana > 2) {
      elementos.push('separador-inicial')
    }
  }
  for (let pagina = inicioVentana; pagina <= finVentana; pagina += 1) {
    elementos.push(pagina)
  }
  if (finVentana < totalPaginas) {
    if (finVentana < totalPaginas - 1) {
      elementos.push('separador-final')
    }
    elementos.push(totalPaginas)
  }
  return elementos
}

export function Paginacion({ paginaActual, totalPaginas, alCambiarPagina, etiqueta }: PropiedadesPaginacion) {
  if (totalPaginas <= 1) {
    return null
  }
  return (
    <nav className="paginacion" aria-label={etiqueta}>
      <button
        type="button"
        className="paginacion__boton"
        aria-label="Página anterior"
        disabled={paginaActual <= 1}
        onClick={() => alCambiarPagina(paginaActual - 1)}
      >
        ‹
      </button>
      {calcularElementos(paginaActual, totalPaginas).map((elemento) =>
        typeof elemento === 'number' ? (
          <button
            key={elemento}
            type="button"
            className="paginacion__boton"
            aria-label={`Página ${elemento}`}
            aria-current={elemento === paginaActual ? 'page' : undefined}
            onClick={() => alCambiarPagina(elemento)}
          >
            {elemento}
          </button>
        ) : (
          <span key={elemento} className="paginacion__separador" aria-hidden="true">
            …
          </span>
        ),
      )}
      <button
        type="button"
        className="paginacion__boton"
        aria-label="Página siguiente"
        disabled={paginaActual >= totalPaginas}
        onClick={() => alCambiarPagina(paginaActual + 1)}
      >
        ›
      </button>
    </nav>
  )
}
