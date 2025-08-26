
import React from 'react';
import { users } from '../constants';

interface HeaderProps {
    onMenuClick: () => void;
}

const Header: React.FC<HeaderProps> = ({ onMenuClick }) => {
  const currentUser = users['user1'];

  return (
    <header className="flex-shrink-0 bg-gray-800 border-b border-gray-700 px-4 md:px-6 lg:px-8">
      <div className="flex items-center justify-between h-16">
        <div className="flex items-center">
            <button
                onClick={onMenuClick}
                className="p-2 rounded-md text-gray-400 hover:text-white hover:bg-gray-700 md:hidden mr-3"
                aria-label="Open menu"
            >
                <svg className="w-6 h-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
            </button>
            <div className="relative w-full max-w-xs hidden sm:block">
                <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                    <svg className="w-5 h-5 text-gray-400" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" x2="16.65" y1="21" y2="16.65"/></svg>
                </div>
                <input
                    type="text"
                    placeholder="Search meetings or transcripts..."
                    className="w-full bg-gray-700 text-white placeholder-gray-400 border border-transparent rounded-lg py-2 pl-10 pr-4 focus:outline-none focus:ring-2 focus:ring-blue-accent focus:border-transparent"
                />
            </div>
        </div>
        <div className="flex items-center space-x-4">
            <button className="p-2 rounded-full hover:bg-gray-700 transition-colors">
                <svg className="w-6 h-6 text-gray-400" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>
            </button>
            <div className="flex items-center space-x-2">
                <img src={currentUser.avatarUrl} alt={currentUser.name} className="w-9 h-9 rounded-full" />
                <div className="text-sm hidden sm:block">
                    <div className="font-medium text-white">{currentUser.name}</div>
                    <div className="text-gray-400">{currentUser.role}</div>
                </div>
                 <svg className="w-5 h-5 text-gray-400 hidden sm:block" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
            </div>
        </div>
      </div>
    </header>
  );
};

export default Header;