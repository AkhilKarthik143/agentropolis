import { BusinessesPage } from '@/pages/BusinessesPage';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { BusinessDetailPage } from '@/pages/BusinessDetailPage';
import { ControlTowerPage } from '@/pages/ControlTowerPage';
import { NegotiationRoomPage } from '@/pages/NegotiationRoomPage';
import { ProcurementPage } from '@/pages/ProcurementPage';
import { ScenariosPage } from '@/pages/ScenariosPage';
import { WorldPage } from '@/pages/WorldPage';
import { MotionEventProvider } from '@/components/motion/MotionEventProvider';

export default function App() {
  return (
    <MotionEventProvider tier="high">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/economy/world" replace />} />
          <Route path="/economy/businesses" element={<BusinessesPage />} />
          <Route path="/economy/world" element={<WorldPage />} />
          <Route path="/economy/negotiations" element={<NegotiationRoomPage />} />
          <Route path="/economy/control-tower" element={<ControlTowerPage />} />
          <Route path="/economy/procurement" element={<ProcurementPage />} />
          <Route path="/economy/scenarios" element={<ScenariosPage />} />
          <Route path="/economy/business/:businessId" element={<BusinessDetailPage />} />
          <Route path="*" element={<Navigate to="/economy/world" replace />} />
        </Routes>
      </BrowserRouter>
    </MotionEventProvider>
  );
}