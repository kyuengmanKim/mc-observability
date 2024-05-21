package mcmp.mc.observability.agent.mapper;

import mcmp.mc.observability.agent.model.MiningDBInfo;
import mcmp.mc.observability.agent.model.dto.MiningDBSetDTO;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface MiningDBMapper {

    int insertMiningDB(MiningDBSetDTO info);

    MiningDBInfo getDetail();

    int deleteMiningDB(Long seq);
}
