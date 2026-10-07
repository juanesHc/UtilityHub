import { HashRouter, Navigate, Route, Routes } from 'react-router'
import { DisenoPanel } from './componentes/DisenoPanel'
import { PaginaAdministradores } from './paginas/administradores/PaginaAdministradores'
import { PaginaCargas } from './paginas/cargas/PaginaCargas'
import { PaginaDetalle } from './paginas/detalle/PaginaDetalle'
import { PaginaDetalleCarga } from './paginas/detalleCarga/PaginaDetalleCarga'
import { PaginaHistorico } from './paginas/historico/PaginaHistorico'
import { PaginaInicio } from './paginas/inicio/PaginaInicio'
import { PaginaLogin } from './paginas/login/PaginaLogin'
import { ProveedorSesion } from './sesion/ProveedorSesion'
import { ProveedorTransicionDeNube } from './transicion/ProveedorTransicionDeNube'

export function App() {
  return (
    <HashRouter>
      <ProveedorSesion>
        <ProveedorTransicionDeNube>
          <Routes>
            <Route path="/login" element={<PaginaLogin />} />
            <Route element={<DisenoPanel />}>
              <Route path="/inicio" element={<PaginaInicio />} />
              <Route path="/historico" element={<PaginaHistorico />} />
              <Route path="/lecturas/:idLectura" element={<PaginaDetalle />} />
              <Route path="/cargas" element={<PaginaCargas />} />
              <Route path="/cargas/:idCarga" element={<PaginaDetalleCarga />} />
              <Route path="/administradores" element={<PaginaAdministradores />} />
            </Route>
            <Route path="*" element={<Navigate to="/inicio" replace />} />
          </Routes>
        </ProveedorTransicionDeNube>
      </ProveedorSesion>
    </HashRouter>
  )
}
