import { useCallback, useEffect, useMemo, useRef } from "react";
import { SERVER_URL } from "@/lib/config";
import { SOUND_EFFECTS } from "@/lib/sounds";

/**
 * Browser audio for the game. One cached <audio> element per sound name.
 *
 * - playSoundEffect({ name, url? }): fire-and-forget. Plays a clone of the
 *   cached element, so the same effect can overlap itself. Accepts the
 *   server's `sound_effect` payload as-is.
 * - playManagedSound(name, { loop }) / stopManagedSound(name): a single
 *   stoppable instance, for the call-a-friend ring and the ticking clock.
 * - primeSoundEffects(): browsers block audio that does not follow a user
 *   gesture. Call this from one (the Start button) so later sounds triggered
 *   by server events are allowed to play.
 *
 * Every sound is preloaded on mount. The returned functions are stable.
 */
export function useSoundEffects() {
  const audioByName = useRef({});
  const activeSounds = useRef({});

  const ensureSoundAudio = useCallback((name, soundUrl = SOUND_EFFECTS[name]) => {
    if (!soundUrl) {
      return null;
    }

    const absoluteUrl = new URL(soundUrl, SERVER_URL).toString();
    let audio = audioByName.current[name];
    if (!audio || audio.src !== absoluteUrl) {
      audio = new Audio(absoluteUrl);
      audio.preload = "auto";
      audioByName.current[name] = audio;
    }

    return audio;
  }, []);

  const playSoundEffect = useCallback(
    (sound) => {
      const name = sound?.name;
      if (!name) {
        return;
      }

      const audio = ensureSoundAudio(name, sound.url || SOUND_EFFECTS[name]);
      if (!audio) {
        return;
      }

      const playback = audio.cloneNode();
      playback.currentTime = 0;
      playback.play().catch(() => {});
    },
    [ensureSoundAudio]
  );

  const playManagedSound = useCallback(
    (name, options = {}) => {
      const audio = ensureSoundAudio(name);
      if (!audio) {
        return;
      }

      audio.pause();
      audio.currentTime = 0;
      audio.loop = Boolean(options.loop);
      activeSounds.current[name] = audio;
      audio.play().catch(() => {});
    },
    [ensureSoundAudio]
  );

  const stopManagedSound = useCallback((name) => {
    const audio = activeSounds.current[name];
    if (!audio) {
      return;
    }

    audio.pause();
    audio.currentTime = 0;
    audio.loop = false;
    delete activeSounds.current[name];
  }, []);

  const primeSoundEffects = useCallback(() => {
    Object.keys(SOUND_EFFECTS).forEach((name) => {
      const audio = ensureSoundAudio(name);
      if (!audio) {
        return;
      }

      audio.muted = true;
      const resetAudio = () => {
        audio.pause();
        audio.currentTime = 0;
        audio.muted = false;
      };
      const playPromise = audio.play();
      if (playPromise) {
        playPromise.then(resetAudio).catch(() => {
          audio.muted = false;
        });
      } else {
        resetAudio();
      }
    });
  }, [ensureSoundAudio]);

  useEffect(() => {
    Object.keys(SOUND_EFFECTS).forEach((name) => {
      ensureSoundAudio(name);
    });
  }, [ensureSoundAudio]);

  return useMemo(
    () => ({ playSoundEffect, playManagedSound, stopManagedSound, primeSoundEffects }),
    [playSoundEffect, playManagedSound, stopManagedSound, primeSoundEffects]
  );
}
