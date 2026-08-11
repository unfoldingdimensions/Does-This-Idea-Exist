"use client";

import { useSyncExternalStore } from "react";
import { getAdminToken, subscribeAdminToken } from "./api";

/**
 * Reactive unlock state: the owner token, or null when locked.
 *
 * Mutating endpoints require the token (MUTATION_AUTH defaults on), so write
 * controls are hidden until it's present — a public visitor should never see a
 * button that answers 403. Server snapshot is null so prerender emits the
 * locked, read-only archive.
 */
export function useAdminToken(): string | null {
  return useSyncExternalStore(subscribeAdminToken, getAdminToken, () => null);
}
