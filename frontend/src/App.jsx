import { useEffect, useState } from "react";
import Header from "./components/Header";
import Footer from "./components/Footer";
import ChatPage from "./pages/ChatPage";
import VoicePage from "./pages/VoicePage";
import KnowledgeBasePage from "./pages/KnowledgeBasePage";
import { getHealth } from "./lib/api";

const HEALTH_POLL_MS = 30_000;

export default function App() {
  const [activeTab, setActiveTab] = useState("chat");
  const [language, setLanguage] = useState("en-IN");
  const [health, setHealth] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const res = await getHealth();
        if (!cancelled) setHealth(res);
      } catch {
        if (!cancelled) setHealth({ status: "error" });
      }
    }

    poll();
    const id = setInterval(poll, HEALTH_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="flex min-h-screen flex-col">
      <Header activeTab={activeTab} onTabChange={setActiveTab} health={health} />

      <main className="flex-1">
        {activeTab === "chat" && <ChatPage language={language} onLanguageChange={setLanguage} />}
        {activeTab === "voice" && <VoicePage language={language} onLanguageChange={setLanguage} />}
        {activeTab === "knowledge-base" && <KnowledgeBasePage />}
      </main>

      <Footer />
    </div>
  );
}
