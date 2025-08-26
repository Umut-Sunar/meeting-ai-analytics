import React from 'react';
import { User, Meeting, AIPrompt, SubscriptionPlan } from './types';

export const ICONS: { [key: string]: React.ReactNode } = {
  Dashboard: <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>,
  Meetings: <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>,
  Analytics: <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18"/><path d="M18.7 8a6 6 0 0 0-6 0"/><path d="M12.7 14a6 6 0 0 0-6 0"/><path d="M8.7 20a6 6 0 0 0-6 0"/></svg>,
  Team: <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>,
  Settings: <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 0 2.12l-.15.1a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l-.22-.38a2 2 0 0 0-.73-2.73l-.15-.1a2 2 0 0 1 0-2.12l.15-.1a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>,
  DesktopApp: <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="20" height="14" x="2" y="3" rx="2"/><line x1="8" x2="16" y1="21" y2="21"/><line x1="12" x2="12" y1="17" y2="21"/></svg>,
  Prompts: <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20.94c1.5 0 2.75 1.06 4 1.06 3 0 6-8 6-12.22A4.91 4.91 0 0 0 17 5c-2.22 0-4 1.44-4 4s1.78 4 4 4c0 2.22-1.78 4-4 4Z"/><path d="M4 12.22V18c0 1.21.57 2.26 1.5 3s2.29 1.06 3.5 1.06c.92 0 1.75-.29 2.5-.81"/><path d="M4 12.22C4 8 7 2 12 2c1.07 0 2.06.37 2.87 1.01"/></svg>,
  SuperAdmin: <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>,
};

export const users: { [key: string]: User } = {
  'user1': { 
    id: 'user1', name: 'Alex Johnson', avatarUrl: 'https://picsum.photos/seed/alex/100/100', role: 'Admin', 
    plan: 'Enterprise', status: 'Active', 
    usage: { minutes: 750, maxMinutes: 5000, tokens: 120000, maxTokens: 1000000 },
    jobDescription: "As a Senior Account Executive, my main role is to manage the full sales cycle, from prospecting and initial outreach to negotiation and closing deals. I focus on understanding customer needs, presenting compelling value propositions, handling objections, and building long-term relationships with key enterprise clients.",
    skills: [
        { id: 'skill1', name: 'Customer Need Analysis', score: 78, description: 'AI analysis: This skill involves effectively questioning and listening to uncover a customer\'s core problems, challenges, and desired business outcomes.' },
        { id: 'skill2', name: 'Value Proposition Delivery', score: 85, description: 'AI analysis: Clearly articulating the unique value of your product/service and how it directly solves the customer\'s identified needs and creates tangible ROI.' },
        { id: 'skill3', name: 'Objection Handling', score: 65, description: 'AI analysis: The ability to address customer concerns, doubts, or disagreements constructively, turning potential roadblocks into opportunities for clarification and trust-building.' },
        { id: 'skill4', name: 'Closing Technique', score: 72, description: 'AI analysis: Guiding the conversation towards a clear decision, confidently asking for the business, and defining next steps to move the deal forward.' },
    ]
  },
  'user2': { 
    id: 'user2', name: 'Maria Garcia', avatarUrl: 'https://picsum.photos/seed/maria/100/100', role: 'Member', 
    plan: 'Pro', status: 'Active',
    usage: { minutes: 240, maxMinutes: 800, tokens: 45000, maxTokens: 100000 }
  },
  'user3': { 
    id: 'user3', name: 'Chen Wei', avatarUrl: 'https://picsum.photos/seed/chen/100/100', role: 'Member',
    plan: 'Pro', status: 'Active',
    usage: { minutes: 600, maxMinutes: 800, tokens: 89000, maxTokens: 100000 }
  },
  'user4': { 
    id: 'user4', name: 'Emily Carter', avatarUrl: 'https://picsum.photos/seed/emily/100/100', role: 'Member',
    plan: 'Free', status: 'Suspended',
    usage: { minutes: 50, maxMinutes: 60, tokens: 8000, maxTokens: 10000 }
  },
  'user5': {
    id: 'user5', name: 'Samantha Green', avatarUrl: 'https://picsum.photos/seed/samantha/100/100', role: 'Member',
    plan: 'Pro', status: 'Active',
    usage: { minutes: 320, maxMinutes: 800, tokens: 65000, maxTokens: 100000 }
  },
  'user6': {
    id: 'user6', name: 'David Brown', avatarUrl: 'https://picsum.photos/seed/david/100/100', role: 'Manager',
    plan: 'Enterprise', status: 'Active',
    usage: { minutes: 1200, maxMinutes: 5000, tokens: 250000, maxTokens: 1000000 }
  },
  'user7': {
    id: 'user7', name: 'Olivia White', avatarUrl: 'https://picsum.photos/seed/olivia/100/100', role: 'Member',
    plan: 'Free', status: 'Active',
    usage: { minutes: 45, maxMinutes: 60, tokens: 9000, maxTokens: 10000 }
  },
  'user8': {
    id: 'user8', name: 'James Black', avatarUrl: 'https://picsum.photos/seed/james/100/100', role: 'Member',
    plan: 'Pro', status: 'Suspended',
    usage: { minutes: 750, maxMinutes: 800, tokens: 95000, maxTokens: 100000 }
  },
  'user9': {
    id: 'user9', name: 'Sophia Rodriguez', avatarUrl: 'https://picsum.photos/seed/sophia/100/100', role: 'Admin',
    plan: 'Enterprise', status: 'Active',
    usage: { minutes: 2500, maxMinutes: 5000, tokens: 500000, maxTokens: 1000000 }
  },
  'user10': {
    id: 'user10', name: 'Liam Wilson', avatarUrl: 'https://picsum.photos/seed/liam/100/100', role: 'Member',
    plan: 'Pro', status: 'Active',
    usage: { minutes: 150, maxMinutes: 800, tokens: 30000, maxTokens: 100000 }
  },
  'user11': {
    id: 'user11', name: 'Isabella Martinez', avatarUrl: 'https://picsum.photos/seed/isabella/100/100', role: 'Member',
    plan: 'Pro', status: 'Active',
    usage: { minutes: 500, maxMinutes: 800, tokens: 75000, maxTokens: 100000 }
  },
  'user12': {
    id: 'user12', name: 'Noah Taylor', avatarUrl: 'https://picsum.photos/seed/noah/100/100', role: 'Manager',
    plan: 'Enterprise', status: 'Suspended',
    usage: { minutes: 4800, maxMinutes: 5000, tokens: 980000, maxTokens: 1000000 }
  },
  'user13': {
    id: 'user13', name: 'Ava Anderson', avatarUrl: 'https://picsum.photos/seed/ava/100/100', role: 'Member',
    plan: 'Free', status: 'Active',
    usage: { minutes: 10, maxMinutes: 60, tokens: 1500, maxTokens: 10000 }
  },
  'user14': {
    id: 'user14', name: 'William Thomas', avatarUrl: 'https://picsum.photos/seed/william/100/100', role: 'Member',
    plan: 'Pro', status: 'Active',
    usage: { minutes: 400, maxMinutes: 800, tokens: 60000, maxTokens: 100000 }
  },
};

export const aiPrompts: AIPrompt[] = [
    { id: 'prompt-general', name: 'General Summary', text: 'Provide a concise overview of the meeting, list the main topics discussed, and extract all action items with owners.', type: 'default', tags: ['Meeting Summary'] },
    { id: 'prompt-sales-summary', name: 'Sales Follow-up Summary', text: 'Analyze this sales call. Identify customer pain points, buying signals, and any objections. Create a list of next steps for the sales team.', type: 'custom', tags: ['Meeting Summary'] },
    { id: 'prompt-tech-summary', name: 'Technical Debrief Summary', text: 'Extract all technical requirements, challenges, and decisions made. List any engineering tasks or follow-ups.', type: 'custom', tags: ['Meeting Summary'] },
    { id: 'prompt-assistant-sales', name: 'Live Sales Coach', text: 'During the meeting, actively listen for customer objections and suggest real-time rebuttals. Identify buying signals and prompt me to ask clarifying questions. Remind me to summarize next steps before the call ends.', type: 'custom', tags: ['Meeting Assistant'] },
    { id: 'prompt-assistant-negotiation', name: 'Negotiation Advisor', text: 'Monitor the negotiation. If the customer mentions budget constraints, suggest pivoting to value-based selling points. If they ask for a discount, provide pre-approved options and talking points.', type: 'custom', tags: ['Meeting Assistant'] },
];

export const subscriptionPlans: SubscriptionPlan[] = [
    {
        id: 'plan-free',
        name: 'Free',
        price: '$0 / month',
        minutes: 60,
        tokens: 10000,
        features: ['Limited transcription', 'Basic AI summary', '3 meetings history']
    },
    {
        id: 'plan-pro',
        name: 'Pro',
        price: '$29 / month',
        minutes: 800,
        tokens: 100000,
        features: ['Unlimited transcription', 'Advanced AI summaries', 'Custom prompts', 'Integrations']
    },
    {
        id: 'plan-enterprise',
        name: 'Enterprise',
        price: 'Custom',
        minutes: 5000,
        tokens: 1000000,
        features: ['All Pro features', 'Super Admin panel', 'Team analytics', 'Priority support']
    }
];

export const meetings: Meeting[] = [
  {
    id: 'm1',
    title: 'Q3 Product Strategy Sync',
    date: '2024-07-22T10:00:00Z',
    duration: 45,
    participants: [users['user1'], users['user2'], users['user3']],
    summaries: {
      'prompt-general': {
        overview: ['Discussed the Q3 product roadmap, focusing on the new "Phoenix" feature launch. Key decisions were made regarding marketing budget and engineering resource allocation.'],
        actionItems: [
          'Alex to finalize the marketing budget by EOD Wednesday.',
          'Maria to create the initial PRD for the "Phoenix" feature.',
          'Chen to scope out the required backend changes for Phoenix.',
        ],
        keyTopics: ['Phoenix Feature', 'Q3 Marketing Budget', 'Engineering Resources', 'Launch Timeline'],
      },
      'prompt-sales-summary': {
          overview: ['The team discussed the upcoming "Phoenix" feature, which is a key deliverable for Q3. The primary focus was on aligning marketing and engineering efforts to ensure a successful launch.'],
          actionItems: [
              'Finalize marketing budget for Phoenix campaign (Owner: Alex).',
              'Draft initial PRD for Phoenix feature (Owner: Maria).'
          ],
          keyTopics: ['Phoenix Feature', 'Launch Strategy', 'Resource Allocation'],
      },
      'prompt-tech-summary': {
        overview: ['Technical discussion centered on backend requirements for the Phoenix feature. The main challenge identified was database scaling to handle anticipated load. A new indexing strategy was proposed as a potential solution.'],
        actionItems: [
            'Scope out backend changes for Phoenix, including database scaling assessment (Owner: Chen).',
        ],
        keyTopics: ['Backend Architecture', 'Database Scaling', 'Indexing Strategy', 'Phoenix Feature'],
      }
    },
    transcript: [
      { speaker: 'user1', speakerLabel: 'Alex Johnson', timestamp: 12, text: "Alright team, let's kick things off. The main topic for today is the Q3 product strategy, specifically the Phoenix feature." },
      { speaker: 'user2', speakerLabel: 'Maria Garcia', timestamp: 35, text: "Thanks, Alex. I've put together some initial thoughts on the user flow. I think we should prioritize a seamless onboarding experience." },
      { speaker: 'user1', speakerLabel: 'Alex Johnson', timestamp: 58, text: "Good point. Chen, what are the potential backend challenges we might face?" },
      { speaker: 'user3', speakerLabel: 'Chen Wei', timestamp: 81, text: "The main challenge will be scaling the database to handle the expected load. We might need to consider a new indexing strategy." },
      { speaker: 'user2', speakerLabel: 'Maria Garcia', timestamp: 121, text: "How does this impact the timeline? We're aiming for a September launch." },
      { speaker: 'user1', speakerLabel: 'Alex Johnson', timestamp: 155, text: "Let's make sure we have a clear plan. Maria, can you draft the PRD, and Chen, you scope the backend work? We'll sync up again on Wednesday." },
    ],
     analytics: {
      talkRatio: [{ name: 'Alex Johnson', value: 40, color: '#3b82f6' }, { name: 'Maria Garcia', value: 35, color: '#8b5cf6' }, { name: 'Chen Wei', value: 25, color: '#10b981' }],
      sentiment: [{time: 0, value: 0.5}, {time: 5, value: 0.6}, {time: 10, value: 0.4}, {time: 15, value: 0.7}, {time: 20, value: 0.8}, {time: 25, value: 0.6}],
    }
  },
  {
    id: 'm2',
    title: 'Acme Corp. Client Pitch',
    date: '2024-07-21T14:00:00Z',
    duration: 62,
    participants: [users['user1'], users['user4']],
     summaries: {
      'prompt-general': {
        overview: ['Pitched our new enterprise solution to Acme Corp. They were particularly interested in the security features and the integration capabilities. Follow-up meeting scheduled for next week.'],
        actionItems: ['Emily to send the follow-up email with pricing details.', 'Alex to prepare a technical demo for the next meeting.'],
        keyTopics: ['Enterprise Solution', 'Security Features', 'API Integration', 'Pricing Model'],
      },
      'prompt-sales-summary': {
        overview: ['Presented the enterprise solution to Acme Corp. Key buying signals included their focus on security and API integration. A follow-up meeting was secured to discuss technical details and pricing.'],
        actionItems: ['Send follow-up email with pricing Tiers 1 and 2 (Owner: Emily).', 'Prepare a targeted technical demo addressing their integration questions (Owner: Alex).'],
        keyTopics: ['Security Features', 'API Integration', 'Next Steps'],
      },
      'prompt-tech-summary': {
          overview: ['The client, Acme Corp, showed strong interest in the technical aspects of the enterprise solution, specifically end-to-end encryption and the robustness of the API.'],
          actionItems: ['Prepare a technical demo focused on the API endpoints and security architecture (Owner: Alex).'],
          keyTopics: ['API Integration', 'End-to-end Encryption', 'System Architecture'],
      }
    },
    transcript: [
      { speaker: 'user1', speakerLabel: 'Alex Johnson', timestamp: 5, text: "Thank you for meeting with us today. We're excited to show you how our solution can help Acme Corp." },
      { speaker: 'user4', speakerLabel: 'Emily Carter', timestamp: 40, text: "As you can see on this slide, our security architecture is industry-leading, with end-to-end encryption." },
      { speaker: 'user1', speakerLabel: 'Alex Johnson', timestamp: 90, text: "We also offer a robust API for seamless integration with your existing systems. What are your primary concerns around integration?" },
    ],
    analytics: {
      talkRatio: [{ name: 'Alex Johnson', value: 55, color: '#3b82f6' }, { name: 'Emily Carter', value: 45, color: '#ef4444' }],
      sentiment: [{time: 0, value: 0.7}, {time: 5, value: 0.8}, {time: 10, value: 0.6}, {time: 15, value: 0.7}, {time: 20, value: 0.9}, {time: 25, value: 0.8}],
    }
  },
    {
    id: 'm3',
    title: 'Weekly Stand-up',
    date: '2024-07-19T09:00:00Z',
    duration: 15,
    participants: [users['user2'], users['user3'], users['user4']],
    summaries: {
      'prompt-general': {
        overview: ['Quick weekly sync on project statuses. All projects are on track. No major blockers reported.'],
        actionItems: ['Chen to deploy the latest changes to staging.'],
        keyTopics: ['Project Alpha', 'Bug Fixes', 'Staging Deployment'],
      },
       'prompt-sales-summary': {
        overview: ['Internal team sync. No direct sales topics discussed.'],
        actionItems: [],
        keyTopics: ['Internal Updates'],
      },
      'prompt-tech-summary':{
        overview: ['Team confirmed project statuses. Project Alpha UI components are complete. Critical bugs from the last sprint have been resolved. The next step is deployment to the staging environment.'],
        actionItems: ['Deploy latest changes for Project Alpha and bug fixes to the staging environment this afternoon (Owner: Chen).'],
        keyTopics: ['Project Alpha Status', 'Bug Fixes', 'Staging Deployment'],
      }
    },
    transcript: [
        { speaker: 'user2', speakerLabel: 'Maria Garcia', timestamp: 15, text: "Okay, Project Alpha is on schedule. We've completed the UI components." },
        { speaker: 'user4', speakerLabel: 'Emily Carter', timestamp: 45, text: "I've closed all the critical bugs from the last sprint." },
        { speaker: 'user3', speakerLabel: 'Chen Wei', timestamp: 70, text: "Great. I will deploy everything to the staging environment this afternoon." },
    ],
    analytics: {
      talkRatio: [{ name: 'Maria Garcia', value: 33, color: '#8b5cf6' }, { name: 'Chen Wei', value: 34, color: '#10b981' }, { name: 'Emily Carter', value: 33, color: '#ef4444' }],
      sentiment: [{time: 0, value: 0.6}, {time: 2, value: 0.6}, {time: 4, value: 0.7}, {time: 6, value: 0.6}, {time: 8, value: 0.7}, {time: 10, value: 0.7}],
    }
  }
];

export const overallPerformanceData = [
  { name: 'Jan', score: 55 },
  { name: 'Feb', score: 58 },
  { name: 'Mar', score: 65 },
  { name: 'Apr', score: 62 },
  { name: 'May', score: 70 },
  { name: 'Jun', score: 75 },
];

export const skillProgressionData = [
  { name: 'Jan', 'Customer Need Analysis': 60, 'Value Proposition Delivery': 70, 'Objection Handling': 50, 'Closing Technique': 55 },
  { name: 'Feb', 'Customer Need Analysis': 65, 'Value Proposition Delivery': 72, 'Objection Handling': 52, 'Closing Technique': 60 },
  { name: 'Mar', 'Customer Need Analysis': 70, 'Value Proposition Delivery': 78, 'Objection Handling': 58, 'Closing Technique': 65 },
  { name: 'Apr', 'Customer Need Analysis': 72, 'Value Proposition Delivery': 80, 'Objection Handling': 60, 'Closing Technique': 68 },
  { name: 'May', 'Customer Need Analysis': 75, 'Value Proposition Delivery': 82, 'Objection Handling': 62, 'Closing Technique': 70 },
  { name: 'Jun', 'Customer Need Analysis': 78, 'Value Proposition Delivery': 85, 'Objection Handling': 65, 'Closing Technique': 72 },
];

export const aiCoachingTips: { [key: string]: string[] } = {
    'skill1': [ // Customer Need Analysis
        "In the Acme Corp call, you could have asked more open-ended questions to uncover deeper pain points.",
        "Try using the '5 Whys' technique in your next discovery call to get to the root cause of a customer's problem."
    ],
    'skill2': [ // Value Proposition Delivery
        "Excellent use of data points when presenting to Q3 Product Sync. Continue to tie features directly to customer ROI.",
        "Consider creating a short, reusable story that illustrates the main value proposition."
    ],
    'skill3': [ // Objection Handling
        "When handling the budget objection, try to pivot back to value before discussing price. Acknowledge their concern, then reinforce the ROI.",
        "Your response to the timeline concern was good, but could be strengthened by providing a case study of a similar successful implementation."
    ],
    'skill4': [ // Closing Technique
        "You're successfully identifying closing signals. The next step is to use a firmer 'assumptive close' when the signals are strong.",
        "Try to summarize the agreed-upon value points just before asking for the sale to reinforce their decision."
    ]
};
