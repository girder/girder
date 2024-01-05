/// <reference types="vite/client" />
import { type Girder } from '@girder/core';

declare global {
  const girder: Girder;
}
