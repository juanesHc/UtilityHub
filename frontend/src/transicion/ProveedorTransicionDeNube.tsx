import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router'
import { VideoSilencioso } from '../componentes/VideoSilencioso'
import { prefiereMovimientoReducido, rutaMedio } from '../dominio/medios'
import { ContextoTransicion, type EtapaTransicion } from './contextoTransicion'
import './transicionDeNube.css'

const DURACION_CUBRIR_MILISEGUNDOS = 1300
const DURACION_REVELAR_MILISEGUNDOS = 1500

const CLASE_POR_ETAPA: Record<Exclude<EtapaTransicion, 'inactiva'>, string> = {
  preparada: 'nube',
  cubriendo: 'nube nube--cubriendo',
  revelando: 'nube nube--revelando',
}

export function ProveedorTransicionDeNube({ children }: { children: ReactNode }) {
  const navegar = useNavigate()
  const [etapa, establecerEtapa] = useState<EtapaTransicion>('inactiva')
  const temporizadores = useRef<number[]>([])

  useEffect(() => {
    const pendientes = temporizadores.current
    return () => pendientes.forEach((temporizador) => window.clearTimeout(temporizador))
  }, [])

  const prepararTransicion = useCallback(() => {
    establecerEtapa((actual) => (actual === 'inactiva' ? 'preparada' : actual))
    return () => establecerEtapa((actual) => (actual === 'preparada' ? 'inactiva' : actual))
  }, [])

  const iniciarTransicion = useCallback(
    (destino: string) => {
      if (prefiereMovimientoReducido()) {
        establecerEtapa('inactiva')
        navegar(destino, { replace: true })
        return
      }
      establecerEtapa('cubriendo')
      const alCubrir = window.setTimeout(() => {
        navegar(destino, { replace: true })
        establecerEtapa('revelando')
        const alRevelar = window.setTimeout(() => establecerEtapa('inactiva'), DURACION_REVELAR_MILISEGUNDOS)
        temporizadores.current.push(alRevelar)
      }, DURACION_CUBRIR_MILISEGUNDOS)
      temporizadores.current.push(alCubrir)
    },
    [navegar],
  )

  const valor = useMemo(
    () => ({ etapa, prepararTransicion, iniciarTransicion }),
    [etapa, prepararTransicion, iniciarTransicion],
  )

  return (
    <ContextoTransicion.Provider value={valor}>
      {children}
      {etapa !== 'inactiva' && (
        <div className="nube-contenedor" aria-hidden="true">
          <div className={CLASE_POR_ETAPA[etapa]}>
            <div className="nube__velo" />
            <VideoSilencioso className="nube__textura" fuente={rutaMedio('nube.mp4')} />
            <VideoSilencioso className="nube__banda nube__banda--segunda" fuente={rutaMedio('nube.mp4')} />
            <VideoSilencioso className="nube__banda nube__banda--primera" fuente={rutaMedio('nube.mp4')} />
          </div>
        </div>
      )}
    </ContextoTransicion.Provider>
  )
}
