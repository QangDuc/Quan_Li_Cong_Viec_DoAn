import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { installMockApi } from './mockApi.ts'

// Tự động kích hoạt Mock API khi Backend offline để thuận tiện phát triển & chỉnh sửa Frontend
installMockApi()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
