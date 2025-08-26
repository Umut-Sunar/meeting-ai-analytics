"""
Initial seed data for testing the database schema.
Creates: 1 tenant + 2 users + 1 team + 1 meeting
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from app.database.connection import AsyncSessionLocal
from app.models import (
    User, Team, TeamMember, Meeting, Plan, Subscription, Quota,
    Skill, SkillAssessment, Device
)
from app.models.enums import (
    UserRole, UserProvider, UserStatus, TeamRole, 
    MeetingPlatform, MeetingStatus, Language, AIMode,
    SubscriptionStatus, OveragePolicy, DevicePlatform,
    SkillCategory
)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_initial_data():
    """Create initial seed data for testing."""
    
    async with AsyncSessionLocal() as session:
        try:
            # Generate a tenant ID for this demo
            tenant_id = uuid.uuid4()
            print(f"🏢 Creating tenant: {tenant_id}")
            
            # Create a basic plan
            basic_plan = Plan(
                name="Basic Plan",
                monthly_price=2900,  # $29.00
                meeting_minutes_limit=500,
                token_limit=50000,
                features={
                    "max_users": 10,
                    "ai_summaries": True,
                    "transcript_export": True,
                    "basic_analytics": True
                },
                is_active=True
            )
            session.add(basic_plan)
            await session.flush()  # Get the ID
            
            # Create subscription for the tenant
            subscription = Subscription(
                tenant_id=tenant_id,
                plan_id=basic_plan.id,
                status=SubscriptionStatus.ACTIVE,
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=30),
                overage_policy=OveragePolicy.BLOCK
            )
            session.add(subscription)
            
            # Create initial quota
            quota = Quota(
                tenant_id=tenant_id,
                period_start=datetime.utcnow(),
                period_end=datetime.utcnow() + timedelta(days=30),
                minutes_used=0,
                tokens_used=0,
                overage_minutes=0,
                overage_tokens=0
            )
            session.add(quota)
            
            # Create admin user
            admin_user = User(
                tenant_id=tenant_id,
                email="admin@meetingai.dev",
                name="Admin User",
                role=UserRole.ADMIN,
                provider=UserProvider.PASSWORD,
                password_hash=pwd_context.hash("admin123"),
                status=UserStatus.ACTIVE,
                job_description="System Administrator"
            )
            session.add(admin_user)
            
            # Create member user  
            member_user = User(
                tenant_id=tenant_id,
                email="member@meetingai.dev", 
                name="Member User",
                role=UserRole.USER,
                provider=UserProvider.PASSWORD,
                password_hash=pwd_context.hash("member123"),
                status=UserStatus.ACTIVE,
                job_description="Sales Representative"
            )
            session.add(member_user)
            
            await session.flush()  # Get user IDs
            
            # Create a team
            team = Team(
                tenant_id=tenant_id,
                name="Development Team",
                description="Core development and engineering team"
            )
            session.add(team)
            await session.flush()
            
            # Add team memberships
            admin_membership = TeamMember(
                team_id=team.id,
                user_id=admin_user.id,
                role_in_team=TeamRole.OWNER
            )
            member_membership = TeamMember(
                team_id=team.id,
                user_id=member_user.id,
                role_in_team=TeamRole.MEMBER
            )
            session.add(admin_membership)
            session.add(member_membership)
            
            # Create a meeting
            meeting = Meeting(
                tenant_id=tenant_id,
                team_id=team.id,
                owner_user_id=admin_user.id,
                title="Sprint Planning Meeting",
                platform=MeetingPlatform.ZOOM,
                start_time=datetime.utcnow() - timedelta(hours=2),
                end_time=datetime.utcnow() - timedelta(hours=1),
                status=MeetingStatus.READY,
                language=Language.EN,
                ai_mode=AIMode.STANDARD,
                tags=["sprint", "planning", "development"]
            )
            session.add(meeting)
            await session.flush()
            
            # Create some skills
            communication_skill = Skill(
                tenant_id=tenant_id,
                name="Clear Communication",
                category=SkillCategory.COMMUNICATION,
                description="Ability to communicate ideas clearly and effectively",
                rubric={
                    "criteria": [
                        "Uses clear and concise language",
                        "Explains complex concepts simply", 
                        "Listens actively to others"
                    ],
                    "scoring": {
                        "excellent": "90-100",
                        "good": "70-89", 
                        "needs_improvement": "0-69"
                    }
                }
            )
            
            leadership_skill = Skill(
                tenant_id=tenant_id,
                name="Meeting Leadership",
                category=SkillCategory.LEADERSHIP,
                description="Ability to lead meetings effectively",
                rubric={
                    "criteria": [
                        "Keeps meeting on track",
                        "Ensures all voices are heard",
                        "Summarizes key decisions"
                    ]
                }
            )
            
            session.add(communication_skill)
            session.add(leadership_skill)
            await session.flush()
            
            # Create skill assessments
            comm_assessment = SkillAssessment(
                user_id=admin_user.id,
                meeting_id=meeting.id,
                skill_id=communication_skill.id,
                score=85,
                evidence="Clearly explained technical concepts during the meeting",
                improvement_notes="Could ask more clarifying questions"
            )
            
            leadership_assessment = SkillAssessment(
                user_id=admin_user.id,
                meeting_id=meeting.id,
                skill_id=leadership_skill.id,
                score=92,
                evidence="Effectively guided the team through sprint planning",
                improvement_notes="Excellent meeting facilitation"
            )
            
            session.add(comm_assessment)
            session.add(leadership_assessment)
            
            # Create a device registration
            device = Device(
                user_id=admin_user.id,
                platform=DevicePlatform.MACOS,
                machine_fingerprint="mac-001-dev-machine",
                app_version="1.0.0-beta",
                last_seen_at=datetime.utcnow()
            )
            session.add(device)
            
            # Commit all changes
            await session.commit()
            
            print("✅ Successfully created initial data:")
            print(f"   📧 Admin User: admin@meetingai.dev (password: admin123)")
            print(f"   📧 Member User: member@meetingai.dev (password: member123)")
            print(f"   👥 Team: {team.name}")
            print(f"   📅 Meeting: {meeting.title}")
            print(f"   🎯 Skills: {len([communication_skill, leadership_skill])} skills created")
            print(f"   📊 Assessments: {len([comm_assessment, leadership_assessment])} assessments created")
            print(f"   💰 Subscription: {subscription.status} plan")
            print(f"   🖥️  Device: {device.platform} registered")
            
            return {
                "tenant_id": tenant_id,
                "admin_user_id": admin_user.id,
                "member_user_id": member_user.id,
                "team_id": team.id,
                "meeting_id": meeting.id
            }
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error creating seed data: {e}")
            raise


async def main():
    """Main function to run seed data creation."""
    print("🚀 Creating initial seed data...")
    result = await create_initial_data()
    print(f"🎉 Seed data creation completed!")
    return result


if __name__ == "__main__":
    asyncio.run(main())
