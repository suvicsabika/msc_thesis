import { BrowserRouter, Route, Routes } from "react-router-dom";
import TicketDashboard from "./pages/TicketDashboard";
import TicketDetailPage from "./pages/TicketDetailPage";
import TicketSubmissionPage from "./pages/TicketSubmissionPage";
import NotFoundPage from "./pages/NotFoundPage";
import HomePage from "./pages/HomePage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/dashboard" element={<TicketDashboard />} />
        <Route path="/tickets/new" element={<TicketSubmissionPage />} />
        <Route path="/tickets/:ticketId" element={<TicketDetailPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}
