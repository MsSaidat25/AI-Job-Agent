/** React Navigation param list types */

export type RootStackParamList = {
  Onboarding: undefined;
  Main: undefined;
};

export type OnboardingStackParamList = {
  Welcome: undefined;
  ProfileSetup: { parsedData?: Record<string, unknown> };
};

export type HomeStackParamList = {
  Dashboard: undefined;
  JobDetail: { jobId: string };
};

export type SearchStackParamList = {
  JobSearch: undefined;
  JobDetail: { jobId: string };
  GenerateResume: { jobId: string };
  GenerateCoverLetter: { jobId: string };
  DocumentPreview: { content: string; atsScore?: number; missingKeywords?: string[] };
};

export type ApplicationsStackParamList = {
  KanbanBoard: undefined;
  ApplicationDetail: { applicationId: string };
};

export type ChatStackParamList = {
  Chat: undefined;
};

export type ProfileStackParamList = {
  Profile: undefined;
  Settings: undefined;
  ResumeUpload: undefined;
};
