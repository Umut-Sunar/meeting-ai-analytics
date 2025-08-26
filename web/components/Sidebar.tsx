import React from 'react';
import { Page, User } from '../types';
import { ICONS, users } from '../constants';

interface SidebarProps {
  activePage: Page;
  setActivePage: (page: Page) => void;
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activePage, setActivePage, isOpen, setIsOpen }) => {
  const navItems: Page[] = ['Dashboard', 'Meetings', 'Analytics', 'Team', 'Prompts', 'DesktopApp', 'Settings'];
  const currentUser: User = users['user1']; // Assume current user for demo

  const NavLink: React.FC<{ page: Page }> = ({ page }) => {
    const isActive = activePage === page;
    let pageName = page as string;
    if (page === 'DesktopApp') pageName = 'Desktop App';
    if (page === 'SuperAdmin') pageName = 'Super Admin';
    
    return (
      <button
        onClick={() => setActivePage(page)}
        className={`flex items-center w-full px-4 py-3 text-sm font-medium rounded-lg transition-colors duration-200 ${
          isActive
            ? 'bg-blue-accent text-white'
            : 'text-gray-400 hover:bg-gray-700 hover:text-white'
        }`}
      >
        <span className="mr-3">{ICONS[page]}</span>
        {pageName}
      </button>
    );
  };

  return (
    <aside className={`w-64 bg-gray-800 p-4 flex flex-col border-r border-gray-700 fixed inset-y-0 left-0 z-30 transform transition-transform duration-300 ease-in-out md:static md:translate-x-0 ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center">
            <div className="bg-blue-accent p-2 rounded-lg mr-3">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a3.12 3.12 0 0 1 3 3.99V12a3.12 3.12 0 0 1-3 3.99z"/><path d="M12 2a3.12 3.12 0 0 0-3 3.99V12a3.12 3.12 0 0 0 3 3.99z"/><line x1="12" x2="12" y1="19" y2="22"/><line x1="8" x2="16" y1="20" y2="20"/></svg>
            </div>
            <h1 className="text-xl font-bold text-white">MeetingAI</h1>
        </div>
        <button onClick={() => setIsOpen(false)} className="md:hidden text-gray-400 hover:text-white" aria-label="Close menu">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
        </button>
      </div>
      <nav className="flex-1 space-y-2">
        {navItems.map((page) => (
          <NavLink key={page} page={page} />
        ))}
      </nav>
      <div className="mt-auto">
        {currentUser.role === 'Admin' && (
          <div className="pt-2 mt-2 border-t border-gray-700">
            <NavLink page="SuperAdmin" />
          </div>
        )}
      </div>
    </aside>
  );
};

export default Sidebar;