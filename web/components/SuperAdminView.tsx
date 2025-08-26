import React, { useState, useMemo } from 'react';
import { users as allUsers, subscriptionPlans } from '../constants';
import { User, SubscriptionPlan } from '../types';

const StatCard: React.FC<{ title: string; value: string; icon: React.ReactNode }> = ({ title, value, icon }) => (
    <div className="bg-gray-800 p-4 rounded-xl border border-gray-700 flex items-center">
        <div className="p-3 rounded-lg bg-gray-700 mr-4">{icon}</div>
        <div>
            <h4 className="text-sm font-medium text-gray-400">{title}</h4>
            <p className="text-2xl font-bold text-white">{value}</p>
        </div>
    </div>
);

const SuperAdminView: React.FC = () => {
    const [users, setUsers] = useState<User[]>(Object.values(allUsers));
    const [plans, setPlans] = useState<SubscriptionPlan[]>(subscriptionPlans);
    const [searchTerm, setSearchTerm] = useState('');
    const [statusFilter, setStatusFilter] = useState('All');
    const [planFilter, setPlanFilter] = useState('All');
    const [selectedUsers, setSelectedUsers] = useState<string[]>([]);
    const [openActionMenu, setOpenActionMenu] = useState<string | null>(null);


    const totalUsers = users.length;
    const totalMinutes = users.reduce((acc, user) => acc + (user.usage?.minutes || 0), 0);
    const totalTokens = users.reduce((acc, user) => acc + (user.usage?.tokens || 0), 0);
    
    const getStatusColor = (status?: string) => {
        switch (status) {
            case 'Active': return 'bg-green-900 text-green-300';
            case 'Suspended': return 'bg-red-900 text-red-300';
            default: return 'bg-gray-700 text-gray-300';
        }
    };
    
    const getPlanColor = (plan?: string) => {
        switch (plan) {
            case 'Enterprise': return 'border-purple-accent text-purple-300';
            case 'Pro': return 'border-blue-accent text-blue-300';
            case 'Free': return 'border-gray-500 text-gray-400';
            default: return 'border-gray-600 text-gray-300';
        }
    };

    const filteredUsers = useMemo(() => {
        return users
            .filter(user => user.name.toLowerCase().includes(searchTerm.toLowerCase()))
            .filter(user => statusFilter === 'All' || user.status === statusFilter)
            .filter(user => planFilter === 'All' || user.plan === planFilter)
    }, [users, searchTerm, statusFilter, planFilter]);

    const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.checked) {
            setSelectedUsers(filteredUsers.map(u => u.id));
        } else {
            setSelectedUsers([]);
        }
    };

    const handleSelectUser = (userId: string) => {
        setSelectedUsers(prev => 
            prev.includes(userId) ? prev.filter(id => id !== userId) : [...prev, userId]
        );
    };

    const isAllSelected = selectedUsers.length > 0 && selectedUsers.length === filteredUsers.length;

    return (
        <div className="space-y-8">
            <h2 className="text-3xl font-bold text-white">Super Admin Panel</h2>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard title="Total Users" value={totalUsers.toString()} icon={<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-accent"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>} />
                <StatCard title="Total Minutes Used" value={totalMinutes.toLocaleString()} icon={<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-purple-accent"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>} />
                <StatCard title="Total AI Tokens" value={(totalTokens / 1000).toFixed(1) + 'k'} icon={<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-green-400"><path d="M12 20.94c1.5 0 2.75 1.06 4 1.06 3 0 6-8 6-12.22A4.91 4.91 0 0 0 17 5c-2.22 0-4 1.44-4 4s1.78 4 4 4c0 2.22-1.78 4-4 4Z"/><path d="M4 12.22V18c0 1.21.57 2.26 1.5 3s2.29 1.06 3.5 1.06c.92 0 1.75-.29 2.5-.81"/><path d="M4 12.22C4 8 7 2 12 2c1.07 0 2.06.37 2.87 1.01"/></svg>} />
                <StatCard title="Active Subscriptions" value={users.filter(u => u.status === 'Active').length.toString()} icon={<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-yellow-400"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>} />
            </div>

            {/* User Management */}
            <div className="bg-gray-800 rounded-xl border border-gray-700">
                <div className="p-4 border-b border-gray-700">
                    <h3 className="text-lg font-semibold text-white">User Management</h3>
                    <p className="text-sm text-gray-400">Manage all users, their plans, and their platform usage.</p>
                </div>
                 {/* Filters and Actions */}
                <div className="p-4 flex flex-col sm:flex-row justify-between items-center gap-4">
                    <div className="relative w-full sm:max-w-xs">
                        <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                             <svg className="w-5 h-5 text-gray-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" x2="16.65" y1="21" y2="16.65"/></svg>
                        </div>
                        <input type="text" placeholder="Search by name..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="w-full bg-gray-700 text-white placeholder-gray-400 border border-gray-600 rounded-lg py-2 pl-10 pr-4 focus:outline-none focus:ring-2 focus:ring-blue-accent" />
                    </div>
                    <div className="flex items-center gap-2">
                        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-sm text-white focus:ring-blue-accent focus:border-blue-accent">
                            <option value="All">All Statuses</option>
                            <option value="Active">Active</option>
                            <option value="Suspended">Suspended</option>
                        </select>
                        <select value={planFilter} onChange={e => setPlanFilter(e.target.value)} className="bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-sm text-white focus:ring-blue-accent focus:border-blue-accent">
                            <option value="All">All Plans</option>
                            <option value="Free">Free</option>
                            <option value="Pro">Pro</option>
                            <option value="Enterprise">Enterprise</option>
                        </select>
                        <button className="bg-blue-accent text-white px-4 py-2 rounded-lg font-semibold hover:bg-blue-600 transition-colors whitespace-nowrap">+ Add User</button>
                    </div>
                </div>
                <div className="overflow-auto max-h-[600px]">
                    <table className="min-w-full divide-y divide-gray-700">
                        <thead className="sticky top-0 z-10 bg-gray-800">
                            <tr>
                                <th className="px-6 py-3 text-left">
                                    <input type="checkbox" className="h-4 w-4 rounded bg-gray-700 border-gray-600 text-blue-accent focus:ring-blue-accent" checked={isAllSelected} onChange={handleSelectAll} aria-label="Select all users" />
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">User</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Plan</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Role</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Usage</th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-700">
                            {filteredUsers.map(user => (
                                <tr key={user.id} className={selectedUsers.includes(user.id) ? 'bg-blue-accent/10' : ''}>
                                     <td className="px-6 py-4 whitespace-nowrap">
                                        <input type="checkbox" className="h-4 w-4 rounded bg-gray-700 border-gray-600 text-blue-accent focus:ring-blue-accent" checked={selectedUsers.includes(user.id)} onChange={() => handleSelectUser(user.id)} aria-label={`Select ${user.name}`} />
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex items-center">
                                            <img className="h-8 w-8 rounded-full" src={user.avatarUrl} alt="" />
                                            <div className="ml-3">
                                                <div className="text-sm font-medium text-white">{user.name}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(user.status)}`}>
                                            {user.status}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`px-2 py-1 text-xs font-semibold rounded-md border ${getPlanColor(user.plan)}`}>
                                            {user.plan}
                                        </span>
                                    </td>
                                     <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{user.role}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300 min-w-[200px]">
                                        {user.usage && (
                                            <div className="space-y-2">
                                                <div>
                                                    <div className="flex justify-between text-xs mb-1">
                                                        <span>Mins: {user.usage.minutes.toLocaleString()} / {user.usage.maxMinutes.toLocaleString()}</span>
                                                        <span>{((user.usage.minutes / user.usage.maxMinutes) * 100).toFixed(0)}%</span>
                                                    </div>
                                                    <div className="w-full bg-gray-600 rounded-full h-1.5"><div className="bg-blue-accent h-1.5 rounded-full" style={{width: `${(user.usage.minutes / user.usage.maxMinutes) * 100}%`}}></div></div>
                                                </div>
                                                <div>
                                                    <div className="flex justify-between text-xs mb-1">
                                                        <span>Tokens: {user.usage.tokens.toLocaleString()} / {user.usage.maxTokens.toLocaleString()}</span>
                                                        <span>{((user.usage.tokens / user.usage.maxTokens) * 100).toFixed(0)}%</span>
                                                    </div>
                                                    <div className="w-full bg-gray-600 rounded-full h-1.5"><div className="bg-purple-accent h-1.5 rounded-full" style={{width: `${(user.usage.tokens / user.usage.maxTokens) * 100}%`}}></div></div>
                                                </div>
                                            </div>
                                        )}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                        <div className="relative inline-block text-left">
                                            <button onClick={() => setOpenActionMenu(openActionMenu === user.id ? null : user.id)} className="p-2 rounded-full hover:bg-gray-700">
                                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/></svg>
                                            </button>
                                            {openActionMenu === user.id && (
                                                <div className="origin-top-right absolute right-0 mt-2 w-40 rounded-md shadow-lg bg-gray-700 ring-1 ring-black ring-opacity-5 z-10">
                                                    <div className="py-1" role="menu" aria-orientation="vertical" aria-labelledby="options-menu">
                                                        <a href="#" className="block px-4 py-2 text-sm text-gray-300 hover:bg-gray-600 hover:text-white" role="menuitem">Edit User</a>
                                                        <a href="#" className="block px-4 py-2 text-sm text-red-400 hover:bg-gray-600 hover:text-red-300" role="menuitem">Suspend</a>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Subscription Plans */}
            <div>
                <h3 className="text-xl font-bold text-white mb-4">Subscription Plan Management</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {plans.map(plan => (
                        <div key={plan.id} className={`bg-gray-800 p-6 rounded-xl border-2 ${getPlanColor(plan.name).replace(/text-\w+-\d+/,'')}`}>
                            <h4 className="text-lg font-bold text-white">{plan.name} Plan</h4>
                            <p className="text-2xl font-bold text-white mt-2">{plan.price}</p>
                            <div className="space-y-4 mt-4">
                                <div>
                                    <label className="text-sm font-medium text-gray-400">Meeting Minutes</label>
                                    <input type="number" defaultValue={plan.minutes} className="mt-1 w-full bg-gray-700 text-white rounded-md p-2 border border-gray-600 focus:ring-blue-accent focus:border-blue-accent" />
                                </div>
                                <div>
                                    <label className="text-sm font-medium text-gray-400">AI Tokens</label>
                                    <input type="number" defaultValue={plan.tokens} className="mt-1 w-full bg-gray-700 text-white rounded-md p-2 border border-gray-600 focus:ring-blue-accent focus:border-blue-accent" />
                                </div>
                            </div>
                            <div className="mt-6 flex justify-end">
                                <button className="bg-blue-accent text-white px-4 py-2 rounded-lg font-semibold hover:bg-blue-600 transition-colors">Save Changes</button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default SuperAdminView;
