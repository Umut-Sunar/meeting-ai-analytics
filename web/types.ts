export type Page = 'Dashboard' | 'Meetings' | 'Analytics' | 'Team' | 'Settings' | 'MeetingDetail' | 'DesktopApp' | 'Prompts' | 'SuperAdmin';

export interface Skill {
  id: string;
  name: string;
  score: number; // Current score out of 100
  description?: string;
}

export interface User {
  id: string;
  name: string;
  avatarUrl?: string;
  role: 'Admin' | 'Manager' | 'Member';
  plan?: 'Free' | 'Pro' | 'Enterprise';
  status?: 'Active' | 'Suspended';
  usage?: {
    minutes: number;
    maxMinutes: number;
    tokens: number;
    maxTokens: number;
  };
  jobDescription?: string;
  skills?: Skill[];
}

export interface TranscriptSegment {
  speaker: string;
  speakerLabel: string;
  timestamp: number;
  text: string;
  source?: 'mic' | 'sys'; // Dual-source support
}

export interface AIPrompt {
  id: string;
  name: string;
  text: string;
  type: 'default' | 'custom';
  tags?: ('Meeting Summary' | 'Meeting Assistant')[];
}

export interface SubscriptionPlan {
    id: string;
    name: string;
    price: string;
    minutes: number;
    tokens: number;
    features: string[];
}

export interface Meeting {
  id:string;
  title: string;
  date: string;
  duration: number; // in minutes
  participants: User[];
  summaries: {
    [promptId: string]: {
      overview: string[];
      actionItems: string[];
      keyTopics: string[];
    };
  };
  transcript: TranscriptSegment[];
  analytics: {
    talkRatio: { name: string, value: number, color: string }[];
    sentiment: { time: number, value: number }[];
  }
}