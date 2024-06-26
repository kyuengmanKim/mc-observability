package mcmp.mc.observability.agent.controller;

import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import mcmp.mc.observability.agent.common.Constants;
import mcmp.mc.observability.agent.loader.PluginLoader;
import mcmp.mc.observability.agent.model.PluginDefInfo;
import mcmp.mc.observability.agent.model.dto.ResBody;
import mcmp.mc.observability.agent.util.CollectorExecutor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping(Constants.PREFIX_V1)
@RequiredArgsConstructor
public class SystemController {
    private final PluginLoader pluginLoader;
    private final CollectorExecutor collectorExecutor;

    @ApiOperation(value = "Get all available config list")
    @GetMapping("/plugins")
    public ResBody<List<PluginDefInfo>> getPlugins(@RequestParam(required = false) String type) {
        ResBody<List<PluginDefInfo>> resBody = new ResBody<>();
        resBody.setData(type != null? pluginLoader.getPluginDefList(type): pluginLoader.getPluginDefList());
        return resBody;
    }

    @ApiOperation(value = "", hidden = true)
    @GetMapping("/state")
    public Boolean state() {
        return !collectorExecutor.isInactiveAgent();
    }
}
