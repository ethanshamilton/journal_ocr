import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="h-screen w-screen flex">
      {/* Left Side */}
      <div className="w-1/2 p-4 border-r border-gray-300">
        {/* Chat View */}
      </div>
      {/* Right Side */}
      <div className="w-1/2 p-4">
        {/* Note View */}
      </div>
    </div>
  )
}

export default App
