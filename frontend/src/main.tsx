import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import { leerUrlApi } from './api/cliente'
import { AvisoConfiguracion } from './componentes/AvisoConfiguracion'
import './estilos/base.css'

const raiz = document.getElementById('root')
if (raiz === null) {
  throw new Error('No se encontró el elemento raíz de la aplicación')
}

createRoot(raiz).render(<StrictMode>{leerUrlApi() === null ? <AvisoConfiguracion /> : <App />}</StrictMode>)
