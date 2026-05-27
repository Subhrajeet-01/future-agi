import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  onboardingHomeQueryKeys,
  recordActivationEvent,
} from "../api/onboarding-home-api";

export const useRecordActivationEvent = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: recordActivationEvent,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: onboardingHomeQueryKeys.all,
      });
    },
  });
};
