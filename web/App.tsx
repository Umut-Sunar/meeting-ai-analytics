import React, { useState, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import DashboardView from './components/DashboardView';
import MeetingsView from './components/MeetingsView';
import AnalyticsView from './components/AnalyticsView';
import TeamView from './components/TeamView';
import SettingsView from './components/SettingsView';
import Header from './components/Header';
import { Page, Meeting } from './types';
import { meetings as dummyMeetings } from './constants';
import MeetingDetailView from './components/MeetingDetailView';
import DesktopAppView from './components/DesktopAppView';
import PromptsView from './components/PromptsView';
import SuperAdminView from './components/SuperAdminView';


const App: React.FC = () => {
  const [activePage, setActivePage] = useState<Page>('Dashboard');
  const [selectedMeeting, setSelectedMeeting] = useState<Meeting | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const handleSelectMeeting = useCallback((meeting: Meeting) => {
    setSelectedMeeting(meeting);
    setActivePage('MeetingDetail');
    setIsSidebarOpen(false);
  }, []);

  const handleBackToList = useCallback(() => {
    setSelectedMeeting(null);
    setActivePage('Meetings');
  }, []);

  const handleSetActivePage = (page: Page) => {
    setActivePage(page);
    setIsSidebarOpen(false);
  };

  const renderContent = () => {
    if (selectedMeeting && activePage === 'MeetingDetail') {
      return <MeetingDetailView meeting={selectedMeeting} onBack={handleBackToList} />;
    }
    switch (activePage) {
      case 'Dashboard':
        return <DashboardView onSelectMeeting={handleSelectMeeting} />;
      case 'Meetings':
        return <MeetingsView meetings={dummyMeetings} onSelectMeeting={handleSelectMeeting} />;
      case 'Analytics':
        return <AnalyticsView />;
      case 'Team':
        return <TeamView />;
      case 'Prompts':
        return <PromptsView />;
      case 'DesktopApp':
        return <DesktopAppView />;
      case 'SuperAdmin':
        return <SuperAdminView />;
      case 'Settings':
        return <SettingsView />;
      default:
        return <DashboardView onSelectMeeting={handleSelectMeeting} />;
    }
  };

  return (
    <div className="flex h-screen bg-gray-900 text-gray-300 font-sans">
      <Sidebar
        activePage={activePage}
        setActivePage={handleSetActivePage}
        isOpen={isSidebarOpen}
        setIsOpen={setIsSidebarOpen}
      />
      {isSidebarOpen && (
        <div
          onClick={() => setIsSidebarOpen(false)}
          className="fixed inset-0 bg-black/60 z-20 md:hidden"
          aria-hidden="true"
        ></div>
      )}
      <main className="flex-1 flex flex-col overflow-hidden">
        {activePage !== 'DesktopApp' && <Header onMenuClick={() => setIsSidebarOpen(true)} />}
        <div className={`flex-1 overflow-y-auto ${activePage === 'DesktopApp' ? '' : 'p-4 md:p-6 lg:p-8'}`}>
          {renderContent()}
        </div>
      </main>
    </div>
  );
};

export default App;