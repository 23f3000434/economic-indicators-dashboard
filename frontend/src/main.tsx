import { createRoot } from 'react-dom/client';
import { App } from './App';
import './styles.css';
import { RecoveryBoundary } from './PanelParts';

createRoot(document.getElementById('root')!).render(
  <RecoveryBoundary>
    <App />
  </RecoveryBoundary>,
);
