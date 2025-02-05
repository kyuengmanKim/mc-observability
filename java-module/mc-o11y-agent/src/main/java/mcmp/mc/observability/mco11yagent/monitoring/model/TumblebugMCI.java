package mcmp.mc.observability.mco11yagent.monitoring.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
@JsonIgnoreProperties(ignoreUnknown = true)
public class TumblebugMCI {
    private String id;

    private Vm[] vm;

    @Getter
    @Setter
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Vm {
        private String resourceType;

        private String id; // example: "aws-ap-southeast-1"

        private String uid; // example: "wef12awefadf1221edcf"

        private String cspResourceName; // example: "we12fawefadf1221edcf"

        private String cspResourceId; // example: "csp-06eb41e14121c550a"

        private String connectionName;

        private String name; // example: "aws-ap-southeast-1"

        private String subGroupId;

        private String description;

        private String vmUserName;
    }

}
