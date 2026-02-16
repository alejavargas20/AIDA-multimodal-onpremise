export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  kind?: "text" | "file" | "image" | "audio";
  feedback?: 1 | -1;
};

