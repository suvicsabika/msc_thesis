import { BrowserRouter, Route, Routes } from "react-router-dom";
import McpTicketDashboard from "./pages/TicketDashboard";
import TicketDetailPage from "./pages/TicketDetailPage";
import TicketSubmissionPage from "./pages/TicketSubmissionPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<McpTicketDashboard />} />
        <Route path="/tickets/new" element={<TicketSubmissionPage />} />
        <Route path="/tickets/:ticketId" element={<TicketDetailPage />} />
      </Routes>
    </BrowserRouter>
  );
}