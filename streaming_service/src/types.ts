export type Job = {
  id?: string;
  title: string;
  company?: string;
  location?: string;
  url?: string;
  description?: string;
  postedAt?: string; // ISO
  source?: string;
};

export type SearchParams = {
  q?: string;
  location?: string;
  limit?: number;
};

export type StreamMessage = {
  source: string;
  isPartial: boolean;
  jobs: Job[];
};
