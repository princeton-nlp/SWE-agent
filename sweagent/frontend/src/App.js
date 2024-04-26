import Footer from './components/Footer';
import { Routes, Route } from 'react-router-dom';
import Run from './Run';
import Header from './components/Header';
import './static/font.css';
import './static/index.css';

function App() {
  
  return (
    <div>
      <Header />
      <Routes>
        <Route path="/" element={<Run/>} />
      </Routes>
      <Footer />
    </div>
  );
}

export default App;

