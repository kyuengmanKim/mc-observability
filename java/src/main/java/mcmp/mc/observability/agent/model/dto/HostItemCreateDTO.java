package mcmp.mc.observability.agent.model.dto;

import com.fasterxml.jackson.annotation.JsonIgnore;
import io.swagger.annotations.ApiModelProperty;
import lombok.Getter;
import lombok.Setter;
import mcmp.mc.observability.agent.annotation.Base64DecodeField;

@Getter
@Setter
public class HostItemCreateDTO {
    @JsonIgnore
    private Long hostSeq = 0L;
    @ApiModelProperty(value = "Sequence by plugin")
    private Long pluginSeq = 0L;
    @ApiModelProperty(value = "Base64 Encoded value\n" +
            "Monitoring item name")
    @Base64DecodeField
    private String name;
    @ApiModelProperty(value = "Plugin collection interval seconds")
    private Integer intervalSec = 10;
    @ApiModelProperty(value = "Base64 Encoded value\n" +
            "Monitoring item detail configuration  (cf. telegraf plugin configuration)")
    @Base64DecodeField
    private String setting;
}
