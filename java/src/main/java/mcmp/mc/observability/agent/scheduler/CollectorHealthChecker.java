package mcmp.mc.observability.agent.scheduler;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import mcmp.mc.observability.agent.config.ApiProfileCondition;
import mcmp.mc.observability.agent.enums.TelegrafState;
import mcmp.mc.observability.agent.service.HostService;
import mcmp.mc.observability.agent.util.CollectorExecutor;
import mcmp.mc.observability.agent.util.GlobalProperties;
import org.springframework.context.annotation.Conditional;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@Conditional(ApiProfileCondition.class)
@RequiredArgsConstructor
public class CollectorHealthChecker {

    private final CollectorExecutor collectorExecutor;
    private final GlobalProperties globalProperties;
    private final HostService hostService;

    @Scheduled(cron = "${scheduler.expression.health-check:*/3 * * * * ?}")
    public void check() {
        try {
            TelegrafState telegrafState = collectorExecutor.getTelegrafState();

            String uuid = globalProperties.getUuid();
            Long hostSeq = hostService.getHostSeq(uuid);

            hostService.updateTelegrafState(hostSeq, telegrafState);

        } catch (Exception e) {
            e.printStackTrace();
        }
        log.info("Collector Health Check end");
    }
}
