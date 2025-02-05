package mcmp.mc.observability.mco11yagent.trigger.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import mcmp.mc.observability.mco11yagent.trigger.exception.TriggerResultCodeException;
import mcmp.mc.observability.mco11yagent.trigger.mapper.MonitoringConfigStorageMapper;
import mcmp.mc.observability.mco11yagent.trigger.model.TriggerMonitoringConfigInfo;
import mcmp.mc.observability.mco11yagent.monitoring.model.dto.ResBody;
import mcmp.mc.observability.mco11yagent.monitoring.enums.ResultCode;
import mcmp.mc.observability.mco11yagent.monitoring.model.InfluxDBConnector;
import mcmp.mc.observability.mco11yagent.trigger.mapper.TriggerPolicyMapper;
import mcmp.mc.observability.mco11yagent.trigger.mapper.TriggerTargetMapper;
import mcmp.mc.observability.mco11yagent.trigger.mapper.TriggerTargetStorageMapper;
import mcmp.mc.observability.mco11yagent.trigger.model.TriggerPolicyInfo;
import mcmp.mc.observability.mco11yagent.trigger.model.TriggerTargetInfo;
import mcmp.mc.observability.mco11yagent.trigger.model.TriggerTargetStorageInfo;
import mcmp.mc.observability.mco11yagent.trigger.model.dto.ManageTriggerTargetDto;
import mcmp.mc.observability.mco11yagent.trigger.util.TimeConverterUtils;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class TriggerTargetService {

    private final TriggerPolicyMapper triggerPolicyMapper;
    private final TriggerTargetMapper triggerTargetMapper;
    private final TriggerTargetStorageMapper triggerTargetStorageMapper;
    private final MonitoringConfigStorageMapper monitoringConfigStorageMapper;
    private final KapacitorApiService kapacitorApiService;

    public List<TriggerTargetInfo> getList(Long policySeq) {
        TriggerPolicyInfo triggerPolicyInfo = triggerPolicyMapper.getDetail(policySeq);
        if(triggerPolicyInfo == null)
            throw new TriggerResultCodeException(ResultCode.INVALID_REQUEST, "Trigger Policy Sequence Error");

        return triggerTargetMapper.getList(policySeq).stream()
                .peek(this::formatTriggerTargetInfo)
                .collect(Collectors.toList());
    }

    public ResBody<TriggerTargetInfo> getDetail(ResBody<TriggerTargetInfo> ResBody, Long seq) {
        TriggerTargetInfo triggerTargetInfo = getDetail(seq);
        if( triggerTargetInfo == null ) {
            ResBody.setCode(ResultCode.INVALID_REQUEST);
            return ResBody;
        }

        ResBody.setData(triggerTargetInfo);
        return ResBody;
    }

    public TriggerTargetInfo getDetail(Long seq) {
        TriggerTargetInfo info = triggerTargetMapper.getDetail(seq);
        formatTriggerTargetInfo(info);
        return info;
    }

    private void formatTriggerTargetInfo(TriggerTargetInfo target) {
        if (target.getCreateAt() != null) {
            target.setCreateAt(TimeConverterUtils.toUTCFormat(target.getCreateAt()));
        }
        if (target.getUpdateAt() != null) {
            target.setUpdateAt(TimeConverterUtils.toUTCFormat(target.getUpdateAt()));
        }
    }

    public ResBody<Void> setTargets(Long policySeq, List<ManageTriggerTargetDto> targets) {
        ResBody<Void> ResBody = new ResBody<>();
        TriggerPolicyInfo policyInfo = triggerPolicyMapper.getDetail(policySeq);
        if (policyInfo == null)
            throw new TriggerResultCodeException(ResultCode.INVALID_REQUEST, "Trigger Policy Sequence Error");

        List<TriggerTargetInfo> targetInfoList = triggerTargetMapper.getListByPolicySeq(policySeq);
        List<ManageTriggerTargetDto> addTargetList = new ArrayList<>();

        if(!CollectionUtils.isEmpty(targets)) {
            addTargetList.addAll(targets);
            if(!CollectionUtils.isEmpty(targetInfoList)) {
                addTargetList.removeIf(a -> targetInfoList.stream().anyMatch(b -> b.getTargetId().equals(a.getTargetId()) && b.getNsId().equals(a.getNsId())));
                targetInfoList.removeIf(a -> targets.stream().anyMatch(b -> b.getTargetId().equals(a.getTargetId()) && b.getNsId().equals(a.getNsId())));
            }
        }

        try {
            addTriggerTargets(addTargetList, policyInfo);
            deleteTriggerTargets(targetInfoList, policyInfo);
        } catch (Exception e) {
            throw new TriggerResultCodeException(ResultCode.INVALID_REQUEST, "Set Trigger Target failed");
        }

        return ResBody;
    }

    private void addTriggerTargets(List<ManageTriggerTargetDto> addTargetList, TriggerPolicyInfo policyInfo) {
        if (CollectionUtils.isEmpty(addTargetList))
            return;

        Map<String, Object> params = new HashMap<>();
        for (ManageTriggerTargetDto targetDto : addTargetList) {
            TriggerTargetInfo triggerTargetInfo = TriggerTargetInfo.builder()
                    .policySeq(policyInfo.getSeq())
                    .nsId(targetDto.getNsId())
                    .targetId(targetDto.getTargetId())
                    .build();

            triggerTargetMapper.createTarget(triggerTargetInfo);
            Long seq = triggerTargetInfo.getSeq();
            triggerTargetInfo.setSeq(seq);

            params.put("pluginName", "influxdb");
            params.put("notState", "DELETE");
            params.put("targetId", targetDto.getTargetId());
            params.put("nsId", targetDto.getNsId());
            List<TriggerMonitoringConfigInfo> hostStorageInfoList = monitoringConfigStorageMapper.getHostStorageList(params);
            if (CollectionUtils.isEmpty(hostStorageInfoList))
                continue;

            for (TriggerMonitoringConfigInfo info : hostStorageInfoList) {
                InfluxDBConnector influxDBConnector = new InfluxDBConnector(info.getPluginConfig());
                TriggerTargetStorageInfo targetStorageInfo = TriggerTargetStorageInfo.builder()
                        .targetSeq(triggerTargetInfo.getSeq())
                        .url(influxDBConnector.getUrl())
                        .database(influxDBConnector.getDatabase())
                        .retentionPolicy(influxDBConnector.getRetentionPolicy())
                        .build();

                kapacitorApiService.createTask(policyInfo, targetStorageInfo.getUrl(), targetStorageInfo.getDatabase(), targetStorageInfo.getRetentionPolicy());
                triggerTargetStorageMapper.createTargetStorage(targetStorageInfo);
            }
        }
    }

    private void deleteTriggerTargets(List<TriggerTargetInfo> targetInfoList, TriggerPolicyInfo policyInfo) {
        if (CollectionUtils.isEmpty(targetInfoList))
            return;

        for (TriggerTargetInfo targetInfo : targetInfoList) {
            List<Map<String, Object>> taskStorageCountList = triggerTargetStorageMapper.getRemainTaskStorageCount(policyInfo.getSeq());

            int result = triggerTargetStorageMapper.deleteTriggerTargetStorageByTargetSeq(targetInfo.getSeq());
            result += triggerTargetMapper.deleteTriggerTargetBySeq(targetInfo.getSeq());
            if (result == 0)
                continue;

            if (CollectionUtils.isEmpty(taskStorageCountList))
                continue;

            for (Map<String, Object> taskStorage : taskStorageCountList) {
                if(Integer.parseInt(String.valueOf(taskStorage.get("count"))) < 2) {
                    try {
                        kapacitorApiService.deleteTask(targetInfo.getPolicySeq(), String.valueOf(taskStorage.get("url")));
                    } catch (Exception e) {
                        log.error("Failed to delete task. Error : {}, TaskId : {}", e.getMessage(), targetInfo.getPolicySeq());
                    }
                }
            }
        }
    }
}
